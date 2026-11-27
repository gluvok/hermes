"""
stability.py — Scale Weight Stability & Session Trigger Machine
==============================================================
Weight session state machine with 10-second continuous stability detection.
Integrates with WeighbridgeSessionManager for camera captures and ANPR processing.
One transmission per session; resets only when weight returns to zero.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Any

from src.config import config
from src.config.constants import STABILITY_DURATION, STABILITY_TOLERANCE
from src.core.session import session_manager

logger = logging.getLogger(__name__)


class ScaleState(Enum):
    SCALE_IDLE = 0
    SCALE_STABILIZING = 1
    SCALE_STABLE_RECORDED = 2


class ScaleStabilityMachine:
    def __init__(self):
        self.state = ScaleState.SCALE_IDLE
        self.last_weight = 0.0
        self._current_stable_candidate = 0.0
        self._candidate_start_time = 0.0
        self._mid_stability_triggered = False
        self._last_printed_weight = -9999.0
        self._is_online = True
        # UART thread (process_new_weight) and Wi-Fi watchdog (set_network_status) mutate state in parallel on 3.14t
        # ponytail: one coarse lock; an offline abort holds it while reset_session() joins threads (<=0.6s), split if UART latency matters
        self._lock = threading.RLock()

    @property
    def is_online(self) -> bool:
        return self._is_online

    def set_network_status(self, is_online: bool) -> None:
        """Immediately blocks and cancels active weighment session when offline."""
        with self._lock:
            self._is_online = is_online
            if not is_online:
                self.abort_offline_session()

    def abort_offline_session(self) -> None:
        """Aborts active weighment session and resets session manager."""
        with self._lock:
            if self.state != ScaleState.SCALE_IDLE:
                logger.warning("[Scale] Wi-Fi lost. Immediately aborting active weighment session.")
                self._reset_candidate_state()
                session_manager.reset_session()
                from src.devices import led_controller
                led_controller.set_idle()

    def _reset_candidate_state(self):
        self.state = ScaleState.SCALE_IDLE
        self._current_stable_candidate = 0.0
        self._candidate_start_time = 0.0
        self._mid_stability_triggered = False

    def _log_weight_change(self, parsed_weight: float):
        if abs(parsed_weight - self._last_printed_weight) >= 0.1:
            logger.debug(
                f"[Scale] Parsed weight: {parsed_weight:.3f} "
                f"(Threshold: {config.weight_threshold:.1f})"
            )
            self._last_printed_weight = parsed_weight

    def _handle_zero_or_subthreshold(self, parsed_weight: float) -> bool:
        if parsed_weight <= 0.0:
            if self.state != ScaleState.SCALE_IDLE:
                logger.info(
                    "[Scale Session] Weight returned to zero. "
                    "Session closed. Ready for next weighing."
                )
                self._reset_candidate_state()
                session_manager.reset_session()
                from src.devices import led_controller
                led_controller.set_idle()
            return True

        if parsed_weight < config.weight_threshold:
            was_active = self.state != ScaleState.SCALE_IDLE
            self._reset_candidate_state()
            session_manager.reset_session()
            if was_active:
                from src.devices import led_controller
                led_controller.set_idle()
            return True

        return False

    def _evaluate_stability_window(self, parsed_weight: float, now: float):
        duration = getattr(config, "stability_duration", STABILITY_DURATION)
        tolerance = getattr(config, "stability_tolerance", STABILITY_TOLERANCE)
        if abs(parsed_weight - self._current_stable_candidate) <= tolerance:
            elapsed = now - self._candidate_start_time
            if elapsed >= (duration / 2.0) and not self._mid_stability_triggered:
                self._mid_stability_triggered = True
                logger.info(
                    f"[Scale Session] Weight steady for {elapsed:.1f}s (halfway). "
                    "Triggering mid-stability fleet capture & pre-compression..."
                )
                session_manager.trigger_mid_stability_fleet_capture()
            if elapsed >= duration:
                logger.info(
                    f"[Scale Session] Stable weight confirmed ({duration:.1f}s): "
                    f"{self._current_stable_candidate:.3f} kg. Locking stable weight..."
                )
                self.state = ScaleState.SCALE_STABLE_RECORDED
                session_manager.on_weight_stabilized(self._current_stable_candidate)
        else:
            logger.debug(
                f"[Scale] Weight shifted from {self._current_stable_candidate:.3f} "
                f"to {parsed_weight:.3f}. Resetting stability timer."
            )
            self._current_stable_candidate = parsed_weight
            self._candidate_start_time = now
            self._mid_stability_triggered = False

    def process_new_weight(self, parsed_weight: float):
        with self._lock:
            self._process_new_weight(parsed_weight)

    def _process_new_weight(self, parsed_weight: float):
        if not self._is_online:
            return

        now = time.time()
        self.last_weight = parsed_weight
        self._log_weight_change(parsed_weight)

        completed_package = session_manager.check_session_progress()
        if completed_package:
            self._trigger_upload(completed_package)

        if self._handle_zero_or_subthreshold(parsed_weight):
            return

        if self.state == ScaleState.SCALE_STABLE_RECORDED:
            return

        if self.state == ScaleState.SCALE_IDLE:
            session_manager.start_session()
            self.state = ScaleState.SCALE_STABILIZING
            self._current_stable_candidate = parsed_weight
            self._candidate_start_time = now
            logger.info(
                f"[Scale Session] Vehicle detected: {parsed_weight:.1f} kg "
                f"(threshold: {config.weight_threshold:.1f} kg). Stabilizing..."
            )
            from src.devices import led_controller
            led_controller.set_active()
            return

        self._evaluate_stability_window(parsed_weight, now)

    def _trigger_upload(self, session_package: dict[str, Any]) -> str:
        """Transmits session directly to Gluvok Cloud if online; drops if offline."""
        session_id = str(session_package.get("session_id", "UNKNOWN"))

        if not self._is_online:
            logger.warning(
                f"[Weighment] Wi-Fi offline. Weighment {session_id} discarded."
            )
            from src.core.telemetry import record_system_event, record_unsent_weighment
            record_unsent_weighment()
            record_system_event(
                "WEIGHMENT_DISCARDED",
                f"Session {session_id} discarded: Wi-Fi offline",
            )
            return session_id

        logger.info(f"[Weighment] Transmitting session {session_id} directly to cloud...")
        threading.Thread(
            target=self._transmit_online_weighment,
            args=(session_package,),
            name=f"CloudUpload_{session_id}",
            daemon=True,
        ).start()
        return session_id

    def _transmit_online_weighment(self, session_package: dict[str, Any]) -> None:
        from src.config.constants import LED_CLOUD_SUCCESS_DURATION
        from src.core.telemetry import record_unsent_weighment
        from src.devices import led_controller
        from src.integrations.gluvok import post_to_cloud

        session_id = str(session_package.get("session_id", "UNKNOWN"))
        try:
            ok, entry_id, err, _timed_out = post_to_cloud(session_package)
        except (OSError, RuntimeError, ValueError) as exc:
            logger.error(f"[Weighment] Direct cloud upload error for {session_id}: {exc}")
            record_unsent_weighment()
            return
        if not ok:
            logger.error(f"[Weighment] Cloud upload failed for {session_id}: {err}")
            record_unsent_weighment()
            return
        led_controller.trigger_cloud_success(LED_CLOUD_SUCCESS_DURATION)
        logger.info(f"[Weighment] Uploaded session {session_id} to cloud (entry {entry_id}).")

    def reset(self):
        """Manually reset the state machine."""
        with self._lock:
            self.state = ScaleState.SCALE_IDLE
            self.last_weight = 0.0
            self._current_stable_candidate = 0.0
            self._candidate_start_time = 0.0
            self._last_printed_weight = -9999.0
            session_manager.reset_session()
            from src.devices import led_controller
            led_controller.set_idle()


# Module-level singleton
scale_state_machine = ScaleStabilityMachine()


def process_new_weight(weight: float):
    """Convenience function used by scale driver."""
    scale_state_machine.process_new_weight(weight)


def get_scale_state() -> ScaleState:
    """Expose current state."""
    return scale_state_machine.state


def get_current_weight() -> float:
    return scale_state_machine.last_weight


__all__ = [
    "ScaleStabilityMachine",
    "ScaleState",
    "get_current_weight",
    "get_scale_state",
    "process_new_weight",
    "scale_state_machine",
]
