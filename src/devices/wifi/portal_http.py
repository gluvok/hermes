"""portal_http.py — Lifecycle manager for captive portal HTTP service."""
from __future__ import annotations

import http.server
import logging
import threading

from src.devices.wifi.constants import DEFAULT_DNS_PORT, DEFAULT_PORTAL_PORT
from src.devices.wifi.portal_handlers import CaptivePortalHandler
from src.devices.wifi.portal_redirect import (
    kill_stale_portal_listeners,
    setup_port_forwarding,
    teardown_port_forwarding,
)

logger = logging.getLogger(__name__)


class PortalThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address, daemon_threads = True, True


class CaptiveHTTPServer:
    """Threaded HTTP server serving mobile Wi-Fi portal with port 80 self-healing."""

    def __init__(self, port: int = DEFAULT_PORTAL_PORT, iface: str = "wlan0", dns_port: int = DEFAULT_DNS_PORT) -> None:
        self.port, self.iface, self.dns_port = port, iface, dns_port
        self._server: PortalThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._redirected = False

    def start(self) -> bool:
        if self._server: return True
        kill_stale_portal_listeners(self.port)
        for _ in range(2):
            try:
                self._server = PortalThreadingHTTPServer(("0.0.0.0", self.port), CaptivePortalHandler)
                break
            except (OSError, PermissionError): kill_stale_portal_listeners(self.port)
        if not self._server:
            try:
                self._server = PortalThreadingHTTPServer(("0.0.0.0", 8088), CaptivePortalHandler)
                self.port = 8088
            except (OSError, PermissionError) as e:
                logger.error("Failed binding fallback port 8088: %s", e); return False

        self._redirected = setup_port_forwarding(self.iface, self.port, self.dns_port)
        self._thread = threading.Thread(target=self._server.serve_forever, name="CaptiveHTTP", daemon=True)
        self._thread.start()
        url = "http://10.42.0.1" if (self.port == 80 or self._redirected) else f"http://10.42.0.1:{self.port}"
        logger.info("[WiFi] Captive HTTP portal active at %s (iptables redirect=%s)", url, self._redirected)
        return True

    def stop(self) -> None:
        if self._redirected:
            teardown_port_forwarding(self.iface, self.port, self.dns_port); self._redirected = False
        if self._server:
            try: self._server.shutdown(); self._server.server_close()
            except OSError: pass
            self._server = None
