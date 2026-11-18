"""
wifi — High-Reliability nmcli NetworkManager & Captive Portal Subsystem
======================================================================
Consolidated 2-module architecture:
  - manager.py: NetworkManager Wi-Fi interface, scanning, connections, hotspot, watchdog
  - portal.py: Captive portal DNS/HTTP interception, Option 114 DHCP, RFC 8908
"""

# Backward-compatibility module aliases for existing tests
import sys

from src.devices.wifi import manager, portal
from src.devices.wifi.manager import (
    DEFAULT_GATEWAY_IP,
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    HOTSPOT_CON_NAME,
    SIMULATION_STATE,
    connect_to_wifi,
    get_active_wifi_ssid,
    get_available_networks,
    get_existing_profile,
    get_hotspot_ip,
    get_wifi_interface,
    is_hotspot_active,
    is_network_connected,
    is_nmcli_available,
    is_watchdog_running,
    is_watchdog_suspended,
    is_wifi_connected,
    notify_network_status,
    run_nmcli,
    scan_networks,
    start_emergency_hotspot,
    start_hotspot,
    start_wifi_watchdog,
    stop_emergency_hotspot,
    stop_hotspot,
    stop_wifi_watchdog,
    suspend_watchdog,
)
from src.devices.wifi.portal import (
    DEFAULT_HOSTS,
    NM_CAPPORT_FILE,
    NM_DNSMASQ_DIR,
    CaptiveDNSServer,
    CaptiveHTTPHandler,
    CaptiveHTTPServer,
    CaptivePortalService,
    _build_response,
    ensure_local_domain,
    portal_service,
    setup_nm_capport_config,
    setup_port_forwarding,
    teardown_nm_capport_config,
    teardown_port_forwarding,
)

sys.modules[f"{__name__}.hotspot"] = manager
sys.modules[f"{__name__}.connection"] = manager
sys.modules[f"{__name__}.connectivity"] = manager
sys.modules[f"{__name__}.scanner"] = manager
sys.modules[f"{__name__}.runner"] = manager
sys.modules[f"{__name__}.watchdog"] = manager
sys.modules[f"{__name__}.activity"] = manager
sys.modules[f"{__name__}.constants"] = manager
sys.modules[f"{__name__}.ip"] = manager
sys.modules[f"{__name__}.portal_service"] = portal
sys.modules[f"{__name__}.portal_dns"] = portal
sys.modules[f"{__name__}.portal_http"] = portal
sys.modules[f"{__name__}.portal_hosts"] = portal
sys.modules[f"{__name__}.portal_capport"] = portal
sys.modules[f"{__name__}.portal_redirect"] = portal
sys.modules[f"{__name__}.portal_handlers"] = portal

__all__ = [
    "DEFAULT_GATEWAY_IP",
    "DEFAULT_HOSTS",
    "DEFAULT_HOTSPOT_PASS",
    "DEFAULT_HOTSPOT_SSID",
    "HOTSPOT_CON_NAME",
    "NM_CAPPORT_FILE",
    "NM_DNSMASQ_DIR",
    "SIMULATION_STATE",
    "CaptiveDNSServer",
    "CaptiveHTTPHandler",
    "CaptiveHTTPServer",
    "CaptivePortalService",
    "_build_response",
    "connect_to_wifi",
    "ensure_local_domain",
    "get_active_wifi_ssid",
    "get_available_networks",
    "get_existing_profile",
    "get_hotspot_ip",
    "get_wifi_interface",
    "is_hotspot_active",
    "is_network_connected",
    "is_nmcli_available",
    "is_watchdog_running",
    "is_watchdog_suspended",
    "is_wifi_connected",
    "notify_network_status",
    "portal_service",
    "run_nmcli",
    "scan_networks",
    "setup_nm_capport_config",
    "setup_port_forwarding",
    "start_emergency_hotspot",
    "start_hotspot",
    "start_wifi_watchdog",
    "stop_emergency_hotspot",
    "stop_hotspot",
    "stop_wifi_watchdog",
    "suspend_watchdog",
    "teardown_nm_capport_config",
    "teardown_port_forwarding",
]
