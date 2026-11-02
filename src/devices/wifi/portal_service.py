"""portal_service.py — Unified manager for DNS and HTTP captive portal services."""
from __future__ import annotations

import logging

from src.devices.wifi.constants import (
    DEFAULT_DNS_PORT,
    DEFAULT_GATEWAY_IP,
    DEFAULT_PORTAL_PORT,
)
from src.devices.wifi.portal_capport import (
    setup_nm_capport_config,
    teardown_nm_capport_config,
)
from src.devices.wifi.portal_dns import CaptiveDNSServer
from src.devices.wifi.portal_hosts import ensure_local_domain
from src.devices.wifi.portal_http import CaptiveHTTPServer

logger = logging.getLogger(__name__)


class PortalService:
    def __init__(self) -> None:
        self._dns: CaptiveDNSServer | None = None
        self._http: CaptiveHTTPServer | None = None
        self._active = False

    def is_running(self) -> bool:
        return self._active

    def start(self, ip: str = DEFAULT_GATEWAY_IP, http_port: int = DEFAULT_PORTAL_PORT, dns_port: int = DEFAULT_DNS_PORT, iface: str = "wlan0") -> bool:
        if self._active: return True
        ensure_local_domain("hermes.local")
        self._dns = CaptiveDNSServer(ip=ip, port=dns_port)
        self._http = CaptiveHTTPServer(port=http_port, iface=iface, dns_port=dns_port)
        dns_ok, http_ok = self._dns.start(), self._http.start()
        setup_nm_capport_config(ip, self._http.port if (not self._http._redirected and self._http.port != 80) else 80)
        self._active = http_ok
        logger.info("Captive portal status: HTTP=%s, DNS=%s", http_ok, dns_ok)
        return self._active

    def stop(self) -> None:
        if not self._active and not self._dns and not self._http: return
        teardown_nm_capport_config()
        if self._dns: self._dns.stop(); self._dns = None
        if self._http: self._http.stop(); self._http = None
        self._active = False
        logger.info("Captive portal stopped.")


portal_service = PortalService()

__all__ = ["PortalService", "portal_service"]
