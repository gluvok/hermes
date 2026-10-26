"""src.devices.wifi — Balena-based robust Wi-Fi & captive portal management."""
from __future__ import annotations

from src.devices.wifi.connection import connect_to_wifi, is_connecting
from src.devices.wifi.connectivity import (
    find_wifi_connect_bin,
    get_wifi_interface,
    is_balena_available,
    is_network_connected,
    is_nmcli_available,
    is_wifi_connected,
)
from src.devices.wifi.constants import (
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_WIFI_WATCHDOG_INTERVAL,
    HOTSPOT_CON_NAME,
)
from src.devices.wifi.discovery import get_available_networks, get_existing_profile
from src.devices.wifi.hotspot import (
    has_hotspot_connected,
    is_hotspot_active,
    start_emergency_hotspot,
    stop_emergency_hotspot,
)
from src.devices.wifi.installer import get_target_arch, install_wifi_connect
from src.devices.wifi.watchdog import start_wifi_watchdog, stop_wifi_watchdog

__all__ = [
    "DEFAULT_HOTSPOT_PASS",
    "DEFAULT_HOTSPOT_SSID",
    "DEFAULT_WIFI_WATCHDOG_INTERVAL",
    "HOTSPOT_CON_NAME",
    "connect_to_wifi",
    "find_wifi_connect_bin",
    "get_available_networks",
    "get_existing_profile",
    "get_target_arch",
    "get_wifi_interface",
    "has_hotspot_connected",
    "install_wifi_connect",
    "is_balena_available",
    "is_connecting",
    "is_hotspot_active",
    "is_network_connected",
    "is_nmcli_available",
    "is_wifi_connected",
    "start_emergency_hotspot",
    "start_wifi_watchdog",
    "stop_emergency_hotspot",
    "stop_wifi_watchdog",
]
