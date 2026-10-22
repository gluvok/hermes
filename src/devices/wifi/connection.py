"""connection.py — Wi-Fi client connection and credential management via balena."""
from __future__ import annotations

import logging
import threading
import time

from src.core.wifi_vault import save_wifi_network
from src.devices.led import led_controller
from src.devices.wifi.client import submit_credentials
from src.devices.wifi.connectivity import is_network_connected
from src.devices.wifi.constants import DEFAULT_WIFI_CONNECT_TIMEOUT
from src.devices.wifi.hotspot import (
    is_hotspot_active,
    start_emergency_hotspot,
    stop_emergency_hotspot,
)

logger = logging.getLogger(__name__)
_connection_in_progress = threading.Event()


def is_connecting() -> bool:
    """Check if an active Wi-Fi connection handshake is currently executing."""
    return _connection_in_progress.is_set()


def connect_to_wifi(
    ssid: str, password: str, timeout: float = DEFAULT_WIFI_CONNECT_TIMEOUT
) -> tuple[bool, str]:
    """Connect to a Wi-Fi access point via balena with automatic fallback."""
    if not ssid or not ssid.strip():
        return False, "SSID cannot be empty."
    ssid = ssid.strip()
    _connection_in_progress.set()
    try:
        ok, msg = submit_credentials(ssid, password, timeout)
        if not ok:
            if not is_hotspot_active():
                start_emergency_hotspot()
            led_controller.set_network_status(False)
            return False, msg
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if is_network_connected():
                save_wifi_network(ssid, password)
                stop_emergency_hotspot()
                led_controller.set_network_status(True)
                return True, f"Successfully connected to Wi-Fi: '{ssid}'."
            time.sleep(0.5)
        if not is_hotspot_active():
            save_wifi_network(ssid, password)
            led_controller.set_network_status(True)
            return True, f"Credentials accepted for '{ssid}'."
        start_emergency_hotspot()
        led_controller.set_network_status(False)
        return False, f"Connection to '{ssid}' timed out. Hotspot portal restored."
    finally:
        _connection_in_progress.clear()
