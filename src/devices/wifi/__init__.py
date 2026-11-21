"""src.devices.wifi — Pure nmcli-based Wi-Fi & mobile captive portal management."""
from src.devices.wifi.connection import (
    connect_to_wifi,
    connect_wifi,
    get_active_wifi_ssid,
    get_existing_profile,
)
from src.devices.wifi.connectivity import is_network_connected, is_wifi_connected
from src.devices.wifi.constants import (
    DEFAULT_GATEWAY_IP,
    DEFAULT_HOTSPOT_SSID,
    HOTSPOT_CON_NAME,
)
from src.devices.wifi.hotspot import (
    get_hotspot_ip,
    is_hotspot_active,
    start_emergency_hotspot,
    start_hotspot,
    stop_emergency_hotspot,
    stop_hotspot,
)
from src.devices.wifi.portal_service import PortalService, portal_service
from src.devices.wifi.runner import (
    SIMULATION_STATE,
    get_wifi_interface,
    is_nmcli_available,
    run_nmcli,
)
from src.devices.wifi.scanner import get_available_networks, scan_networks
from src.devices.wifi.watchdog import (
    is_watchdog_running,
    start_wifi_watchdog,
    stop_wifi_watchdog,
)

__all__ = [
    "DEFAULT_GATEWAY_IP", "DEFAULT_HOTSPOT_SSID",
    "HOTSPOT_CON_NAME", "SIMULATION_STATE", "PortalService",
    "connect_to_wifi", "connect_wifi", "get_active_wifi_ssid",
    "get_available_networks", "get_existing_profile", "get_hotspot_ip",
    "get_wifi_interface", "is_hotspot_active", "is_network_connected",
    "is_nmcli_available", "is_watchdog_running", "is_wifi_connected",
    "portal_service", "run_nmcli", "scan_networks",
    "start_emergency_hotspot", "start_hotspot", "start_wifi_watchdog",
    "stop_emergency_hotspot", "stop_hotspot", "stop_wifi_watchdog",
]
