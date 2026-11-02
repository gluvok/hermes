"""watchdog.py — Flap-debounced background Wi-Fi connectivity watchdog."""
from __future__ import annotations

import logging
import threading
import time

from src.devices.wifi import hotspot
from src.devices.wifi.activity import is_nmcli_busy, is_watchdog_suspended
from src.devices.wifi.connectivity import is_network_connected
from src.devices.wifi.hotspot import is_hotspot_active

logger = logging.getLogger(__name__)
_watchdog_thread: threading.Thread | None = None
_running = False

def notify_network_status(online: bool) -> None:
    """Updates LED indicator and scale stability machine network state."""
    for mod, attr in (("src.devices.led", "led_controller"), ("src.core.stability", "scale_state_machine")):
        try: getattr(__import__(mod, fromlist=[attr]), attr).set_network_status(online)
        except (ImportError, AttributeError) as exc: logger.debug("Status update error: %s", exc)

def _watchdog_loop(interval: float = 1.0, threshold: int = 2) -> None:
    fails = 0
    while _running:
        time.sleep(interval)
        if not _running or is_watchdog_suspended() or is_nmcli_busy(): continue
        if is_network_connected():
            fails = 0; notify_network_status(True)
            if is_hotspot_active():
                logger.info("[Watchdog] Internet restored. Stopping emergency hotspot...")
                hotspot.stop_emergency_hotspot()
        else:
            fails += 1
            if fails >= threshold:
                notify_network_status(False)
                if not is_hotspot_active():
                    logger.warning("[Watchdog] Wi-Fi lost (%d fails). Activating hotspot...", fails)
                    hotspot.start_emergency_hotspot()

def start_wifi_watchdog(interval: float = 1.0) -> bool:
    global _watchdog_thread, _running

    if _running and _watchdog_thread and _watchdog_thread.is_alive(): return True
    _running = True
    _watchdog_thread = threading.Thread(target=_watchdog_loop, args=(interval,), name="WiFiWatchdog", daemon=True)
    _watchdog_thread.start(); return True

def stop_wifi_watchdog() -> None:
    global _running, _watchdog_thread
    _running = False
    if _watchdog_thread and _watchdog_thread.is_alive(): _watchdog_thread.join(timeout=2.0)
    _watchdog_thread = None

def is_watchdog_running() -> bool:
    return bool(_running and _watchdog_thread and _watchdog_thread.is_alive())
