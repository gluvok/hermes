"""portal_handlers.py — HTTP request handling for captive portal endpoints."""
from __future__ import annotations

import http.server
import json
from urllib.parse import urlsplit

from src.core.wifi_vault import get_saved_wifi_networks
from src.devices.wifi.connection import connect_to_wifi, get_active_wifi_ssid
from src.devices.wifi.constants import UI_DIR
from src.devices.wifi.hotspot import is_hotspot_active
from src.devices.wifi.scanner import scan_networks

_PROBES = {"/generate_204", "/gen_204", "/hotspot-detect.html", "/canonicalizer.ucs.ed.ac.uk", "/connecttest.txt", "/ncsi.txt", "/success.txt"}
_LOCAL_HOSTS = {"10.42.0.1", "192.168.42.1", "hermes.local", "localhost", "127.0.0.1"}


class CaptivePortalHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None: pass
    def do_HEAD(self) -> None: self.do_GET()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        raw_h = self.headers.get("Host", "").strip()
        host = raw_h.split(":")[0].strip().lower()
        loc = f"http://{raw_h}/wifi" if raw_h and ":" in raw_h else "http://10.42.0.1/wifi"
        if path == "/.well-known/captive-portal":
            payload = {"captive": True, "user-portal-url": loc}
            self.send_response(200); self.send_header("Content-Type", "application/captive+json"); self.send_header("Cache-Control", "no-store"); self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8")); return
        if path in {"/config", "/admin"}:
            self.send_response(302); self.send_header("Location", "http://10.42.0.1:8080/config"); self.send_header("Content-Length", "0"); self.end_headers(); return
        if path not in {"/networks", "/saved", "/status"} and (path in _PROBES or (host and host not in _LOCAL_HOSTS)):
            self.send_response(302); self.send_header("Location", loc); self.send_header("Content-Length", "0"); self.end_headers(); return
        if path == "/networks": self._send_json(scan_networks()); return
        if path == "/saved": self._send_json(get_saved_wifi_networks()); return
        if path == "/status": self._send_json({"hotspot": is_hotspot_active(), "active_ssid": get_active_wifi_ssid()}); return
        html = (UI_DIR / "index.html").read_text(encoding="utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/connect":
            length = int(self.headers.get("Content-Length", 0))
            try: payload = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
            except (json.JSONDecodeError, UnicodeDecodeError): payload = {}
            ssid = payload.get("ssid", "").strip()
            pwd = payload.get("password") or payload.get("passphrase", "")
            ok, msg = connect_to_wifi(ssid, pwd)
            self._send_json({"success": ok, "message": msg}, status=200 if ok else 400); return
        self.send_response(404); self.end_headers()

    def _send_json(self, data: object, status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
        self.wfile.write(raw)


__all__ = ["CaptivePortalHandler"]
