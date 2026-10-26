"""constants.py — Configuration constants for balena-based Wi-Fi setup."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_HOTSPOT_SSID = "hermes"
DEFAULT_HOTSPOT_PASS = "12345678"
HOTSPOT_CON_NAME = "hermes-hotspot"
DEFAULT_PORTAL_GATEWAY = "192.168.42.1"
DEFAULT_PORTAL_DHCP_RANGE = "192.168.42.2,192.168.42.254"

DEFAULT_PORTAL_PORT = 80
DEFAULT_WEB_PORT = 8080

DEFAULT_WIFI_CONNECT_TIMEOUT = 60.0
DEFAULT_WIFI_WATCHDOG_INTERVAL = 10.0
DEFAULT_ACTIVITY_TIMEOUT = 0

BALENA_BINARY_NAMES = (
    "wifi-connect",
    str(BASE_DIR / "bin" / "wifi-connect"),
    str(BASE_DIR.parents[2] / "scripts" / "bin" / "wifi-connect"),
    "/usr/local/sbin/wifi-connect",
    "/usr/local/bin/wifi-connect",
    "/usr/bin/wifi-connect",
)

UI_DIR = BASE_DIR / "ui"
