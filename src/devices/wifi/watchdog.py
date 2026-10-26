"""watchdog.py — Robust background watchdog and automatic hotspot fallback for balena."""
from __future__ import annotations

import logging
import threading

from src.devices.led import led_controller
from src.devices.wifi import connection as conn
from src.devices.wifi import connectivity as cty
from src.devices.wifi import constants as c
from src.devices.wifi import hotspot as hs

logger = logging.getLogger(__name__)
_watchdog_thread: threading.Thread | None = None
_stop_event, _lock = threading.Event(), threading.RLock()


def _handle_status(online: bool, failures: int, threshold: int = 2) -> int:
    from src.core.stability import scale_state_machine
    led_controller.set_network_status(online)
    scale_state_machine.set_network_status(online)
    if online:
        if hs.is_hotspot_active(): hs.stop_emergency_hotspot()
        return 0
    if (failures := failures + 1) >= threshold and not hs.is_hotspot_active() and not conn.is_connecting():
        logger.warning("[Watchdog] Wi-Fi lost. Launching balena captive portal...")
        hs.start_emergency_hotspot()
        return 0
    return failures


def _loop(interval: float) -> None:
    failures = 0
    while not _stop_event.is_set():
        if hs.is_hotspot_active():
            pass
        elif hs.has_hotspot_connected():
            logger.info("[Watchdog] Balena Wi-Fi setup succeeded! Restoring network.")
            hs.stop_emergency_hotspot()
            failures = _handle_status(cty.is_network_connected(), 0)
        elif not conn.is_connecting():
            code, err = hs.get_hotspot_exit_details()
            if code is not None and code != 0:
                logger.error(f"[Watchdog] Balena hotspot exited with code {code}: {err or 'unhandled error'}")
                hs.stop_emergency_hotspot()
                failures = -15
            failures = _handle_status(cty.is_network_connected(), failures) if failures >= 0 else failures + 1
        _stop_event.wait(interval)


def start_wifi_watchdog(interval: float = c.DEFAULT_WIFI_WATCHDOG_INTERVAL) -> None:
    global _watchdog_thread
    with _lock:
        if not (_watchdog_thread and _watchdog_thread.is_alive()):
            _stop_event.clear()
            (_watchdog_thread := threading.Thread(target=_loop, args=(interval,), name="WiFiWatchdog", daemon=True)).start()


def stop_wifi_watchdog(timeout: float = 3.0) -> None:
    global _watchdog_thread
    with _lock:
        _stop_event.set()
        if _watchdog_thread and _watchdog_thread.is_alive(): _watchdog_thread.join(timeout=timeout)
        _watchdog_thread = None
