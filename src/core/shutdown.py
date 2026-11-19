"""
shutdown.py — Graceful Container Shutdown & RS232 Drain Protocol
================================================================
Handles SIGTERM/SIGINT signal trapping for containerized updates.
Guarantees in-flight weighment sessions and SQLite transactions complete
cleanly before serial port closure and process termination.
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Callable, Dict, Set

logger = logging.getLogger(__name__)


class GracefulShutdownDrain:
    def __init__(self, grace_period: float = 30.0, auto_trap_signals: bool = False):
        self.grace_period = grace_period
        self._is_shutting_down = False
        self._active_sessions: Set[str] = set()
        self._lock = threading.Lock()
        self._cleanup_hooks: Dict[str, Callable[[], None]] = {}
        self._drain_event = threading.Event()

        if auto_trap_signals:
            self.register_signal_handlers()

    @property
    def is_shutting_down(self) -> bool:
        with self._lock:
            return self._is_shutting_down

    @property
    def has_active_session(self) -> bool:
        with self._lock:
            return len(self._active_sessions) > 0

    def begin_session(self, session_id: str) -> bool:
        """Register active in-flight session. Refuses new sessions if shutting down."""
        with self._lock:
            if self._is_shutting_down:
                logger.warning(
                    f"[Shutdown] Rejecting new session {session_id}; container is draining."
                )
                return False
            self._active_sessions.add(session_id)
            self._drain_event.clear()
            return True

    def end_session(self, session_id: str) -> None:
        """Mark an in-flight session complete."""
        with self._lock:
            self._active_sessions.discard(session_id)
            if not self._active_sessions:
                self._drain_event.set()

    def register_cleanup_hook(self, name: str, hook: Callable[[], None]) -> None:
        """Register a resource teardown callback (e.g. serial port close, WAL checkpoint)."""
        with self._lock:
            self._cleanup_hooks[name] = hook

    def request_shutdown(self, signum: int | None = None, frame=None) -> None:
        """Signal handler callback or programmatic drain trigger."""
        sig_name = signal.Signals(signum).name if signum else "MANUAL"
        logger.warning(
            f"[Shutdown] Shutdown requested via {sig_name}. Initiating {self.grace_period}s drain..."
        )
        with self._lock:
            self._is_shutting_down = True
            if not self._active_sessions:
                self._drain_event.set()

    def register_signal_handlers(self) -> None:
        """Attach SIGTERM and SIGINT listeners (must be called from main thread)."""
        try:
            signal.signal(signal.SIGTERM, self.request_shutdown)
            signal.signal(signal.SIGINT, self.request_shutdown)
            logger.info("[Shutdown] Trapped SIGTERM and SIGINT for graceful edge drain.")
        except (ValueError, AttributeError) as exc:
            logger.debug(f"[Shutdown] Could not attach signal handlers: {exc}")

    def wait_for_drain(self, timeout: float | None = None) -> bool:
        """
        Wait for in-flight sessions to clear up to timeout (defaults to grace_period).
        Executes cleanup hooks once drained or upon timeout.
        Returns True if all sessions cleared cleanly, False if timed out.
        """
        effective_timeout = timeout if timeout is not None else self.grace_period
        start_time = time.monotonic()

        while True:
            with self._lock:
                if not self._active_sessions:
                    drained = True
                    break
            elapsed = time.monotonic() - start_time
            if elapsed >= effective_timeout:
                logger.error(
                    f"[Shutdown] Drain grace period ({effective_timeout}s) exceeded. "
                    f"Active sessions still pending: {list(self._active_sessions)}"
                )
                drained = False
                break
            time.sleep(0.05)

        # Run registered cleanup hooks
        with self._lock:
            hooks = list(self._cleanup_hooks.items())

        for name, hook in hooks:
            try:
                logger.info(f"[Shutdown] Executing cleanup hook: {name}")
                hook()
            except Exception as e:
                logger.error(f"[Shutdown] Error executing cleanup hook {name}: {e}")

        return drained


# Global singleton instance for Hermes runtime
global_drain = GracefulShutdownDrain()
