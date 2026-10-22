"""watchdog.py — Robust background watchdog and automatic hotspot fallback for balena."""
from __future__ import annotations

import logging
import threading

from src.devices.led import led_controller
from src.devices.wifi.connection import is_connecting
from src.devices.wifi.connectivity import is_network_connected
from src.devices.wifi.constants import DEFAULT_WIFI_WATCHDOG_INTERVAL
from src.devices.wifi.hotspot import (
    is_hotspot_active,
    start_emergency_hotspot,
    stop_emergency_hotspot,
)

logger = logging.getLogger(__name__)
_watchdog_thread: threading.Thread | None = None
_stop_event = threading.Event()
_lock = threading.RLock()


def _handle_status(online: bool, consecutive_failures: int, threshold: int = 2) -> int:
    led_controller.set_network_status(online)
    if online:
        if is_hotspot_active():
            logger.info("[Watchdog] Wi-Fi restored. Stopping balena captive portal.")
            stop_emergency_hotspot()
        return 0
    consecutive_failures += 1
    if consecutive_failures >= threshold and not is_hotspot_active() and not is_connecting():
        logger.warning("[Watchdog] Wi-Fi lost. Launching balena captive portal...")
        start_emergency_hotspot()
    return consecutive_failures


def _loop(interval: float) -> None:
    failures = 0
    while not _stop_event.is_set():
        if not is_connecting():
            failures = _handle_status(is_network_connected(), failures)
        _stop_event.wait(interval)


def start_wifi_watchdog(interval: float = DEFAULT_WIFI_WATCHDOG_INTERVAL) -> None:
    """Start background watchdog thread."""
    global _watchdog_thread
    with _lock:
        if _watchdog_thread and _watchdog_thread.is_alive():
            return
        _stop_event.clear()
        _watchdog_thread = threading.Thread(target=_loop, args=(interval,), name="WiFiWatchdog", daemon=True)
        _watchdog_thread.start()


def stop_wifi_watchdog(timeout: float = 3.0) -> None:
    """Stop background watchdog thread."""
    global _watchdog_thread
    with _lock:
        _stop_event.set()
        if _watchdog_thread and _watchdog_thread.is_alive():
            _watchdog_thread.join(timeout=timeout)
            _watchdog_thread = None
