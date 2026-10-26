"""connectivity.py — Interface detection, network status, and simulation state."""
from __future__ import annotations

import os
import shutil
import socket
from pathlib import Path

from src.devices.wifi.constants import BALENA_BINARY_NAMES

_SIMULATION_STATE = {"is_connected": False, "current_ssid": "", "portal_running": False}


def find_wifi_connect_bin() -> str | None:
    """Find balena wifi-connect binary path."""
    for candidate in BALENA_BINARY_NAMES:
        if candidate.startswith("/"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        elif (found := shutil.which(candidate)) is not None:
            return found
    return None


def is_balena_available() -> bool:
    """Check if balena wifi-connect is installed and runnable."""
    return find_wifi_connect_bin() is not None


def is_nmcli_available() -> bool:
    """Checks if NetworkManager or balena runner is available."""
    return is_balena_available() or shutil.which("nmcli") is not None


def get_wifi_interface() -> str:
    """Detect first available wireless network interface or default to wlan0."""
    sys_net = Path("/sys/class/net")
    if sys_net.is_dir():
        for dev in sys_net.iterdir():
            if (dev / "wireless").is_dir() or dev.name.startswith("wl"):
                return dev.name
    return "wlan0"


def is_network_connected(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.0) -> bool:
    """Robust internet connectivity check via socket connection."""
    if not is_balena_available() and not Path("/sys/class/net").exists():
        return bool(_SIMULATION_STATE["is_connected"])
    for target in ((host, port), ("8.8.8.8", 53)):
        try:
            with socket.create_connection(target, timeout=timeout):
                return True
        except (TimeoutError, OSError):
            continue
    return False


def is_wifi_connected() -> bool:
    """Returns True if connected to an external network (not in AP mode)."""
    return is_network_connected()
