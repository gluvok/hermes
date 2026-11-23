"""constants.py — Configuration constants for pure nmcli Wi-Fi setup."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_HOTSPOT_SSID = "hermes"
HOTSPOT_CON_NAME = "hermes-hotspot"

DEFAULT_GATEWAY_IP = "10.42.0.1"
DEFAULT_PORTAL_PORT = 80
DEFAULT_DNS_PORT = 5354

DEFAULT_WIFI_WATCHDOG_INTERVAL = 1.0

UI_DIR = BASE_DIR / "ui"
