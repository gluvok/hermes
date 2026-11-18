"""portal.py — Captive portal DNS interceptor, HTTP probe redirector, and provisioning service."""
from __future__ import annotations

import http.server
import json
import logging
import os
import shutil
import socket
import socketserver
import subprocess
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

from src.devices.wifi.manager import (
    DEFAULT_DNS_PORT,
    DEFAULT_GATEWAY_IP,
    DEFAULT_HTTP_PORT,
    connect_to_wifi,
    scan_networks,
)

logger = logging.getLogger(__name__)

NM_DNSMASQ_DIR = Path("/etc/NetworkManager/dnsmasq-shared.d")
NM_CAPPORT_FILE = NM_DNSMASQ_DIR / "hermes-captive.conf"
DEFAULT_HOSTS = Path("/etc/hosts")


# ── Captive DNS Interceptor ───────────────────────────────────────────────────
def _build_response(data: bytes, ip: str) -> bytes:
    """Builds a DNS A-record response pointing all queries to the portal gateway IP."""
    if len(data) < 12:
        return b""
    tid = data[:2]
    flags = b"\x81\x80"
    qdcount = b"\x00\x01"
    ancount = b"\x00\x01"
    nscount = b"\x00\x00"
    arcount = b"\x00\x00"

    # Find question section
    idx = 12
    while idx < len(data) and data[idx] != 0:
        idx += 1 + data[idx]
    idx += 5  # null byte + qtype (2) + qclass (2)
    qsection = data[12:idx]

    # Check query type (A vs AAAA)
    qtype = qsection[-4:-2] if len(qsection) >= 4 else b"\x00\x01"

    if qtype == b"\x00\x1c":  # AAAA (IPv6) -> return NOERROR with 0 answers
        return tid + b"\x81\x80" + qdcount + b"\x00\x00\x00\x00\x00\x00" + qsection

    # A record answer
    rname = b"\xc0\x0c"  # pointer to question name
    rtype = b"\x00\x01"  # A
    rclass = b"\x00\x01"  # IN
    ttl = b"\x00\x00\x00\x3c"  # 60 seconds
    rdlen = b"\x00\x04"
    rdata = socket.inet_aton(ip)

    answer = rname + rtype + rclass + ttl + rdlen + rdata
    return tid + flags + qdcount + ancount + nscount + arcount + qsection + answer


class CaptiveDNSServer:
    """Lightweight UDP DNS interceptor resolving all lookups to gateway IP."""

    def __init__(self, ip: str = DEFAULT_GATEWAY_IP, port: int = DEFAULT_DNS_PORT) -> None:
        self.ip = ip
        self.port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("0.0.0.0", self.port))
            self._sock.settimeout(0.5)
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="CaptiveDNS")
            self._thread.start()
            logger.info("[Portal DNS] Bound UDP port :%d redirecting to %s", self.port, self.ip)
            return True
        except OSError as e:
            logger.debug("[Portal DNS] Unable to bind UDP port :%d: %s", self.port, e)
            return False

    def _listen_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                data, addr = self._sock.recvfrom(512)
                resp = _build_response(data, self.ip)
                if resp:
                    self._sock.sendto(resp, addr)
            except (socket.timeout, OSError):
                continue

    def stop(self) -> None:
        self._stop_event.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


# ── Captive HTTP Endpoints & Probe Redirects ─────────────────────────────────
PROBE_PATHS = {
    "/generate_204",
    "/gen_204",
    "/hotspot-detect.html",
    "/canonical.html",
    "/connecttest.txt",
    "/ncsi.txt",
    "/check_network_status.txt",
}

PORTAL_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Gluvok Hermes Setup</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:system-ui,sans-serif;margin:40px auto;max-width:400px;padding:20px;background:#f8fafc}</style>
</head>
<body>
<h2>Gluvok Hermes Wi-Fi Setup</h2>
<p>Connect Hermes to your facility Wi-Fi network.</p>
<form method="POST" action="/connect">
<label>Network (SSID):<br><input name="ssid" style="width:100%" required></label><br><br>
<label>Password:<br><input name="password" type="password" style="width:100%"></label><br><br>
<button type="submit" style="padding:10px 20px;background:#2563eb;color:#fff;border:none;border-radius:4px">Connect</button>
</form>
</body></html>"""


class CaptiveHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress request spam

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in PROBE_PATHS or "connectivitycheck" in self.headers.get("Host", "").lower():
            self.send_response(302)
            self.send_header("Location", f"http://{DEFAULT_GATEWAY_IP}/")
            self.end_headers()
            return

        if path == "/networks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(scan_networks()).encode("utf-8"))
            return

        if path == "/.well-known/captive-portal":
            self.send_response(200)
            self.send_header("Content-Type", "application/captive+json")
            self.end_headers()
            resp = {"captive": True, "user-portal-url": f"http://{DEFAULT_GATEWAY_IP}/"}
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        if path == "/config":
            self.send_response(302)
            self.send_header("Location", f"http://{DEFAULT_GATEWAY_IP}:8080/config")
            self.end_headers()
            return

        # Default: Serve portal page
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PORTAL_HTML.encode("utf-8"))

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/connect":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            params = urllib.parse.parse_qs(body)
            ssid = params.get("ssid", [""])[0]
            pwd = params.get("password", [""])[0]
            ok, msg = connect_to_wifi(ssid, pwd)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            status = "Connected successfully!" if ok else f"Connection failed: {msg}"
            self.wfile.write(f"<h3>{status}</h3><p><a href='/'>Back</a></p>".encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


class CaptiveHTTPServer:
    """Lightweight HTTP server serving the captive sheet and network configuration."""

    def __init__(self, port: int = DEFAULT_HTTP_PORT) -> None:
        self.port = port
        self._server: socketserver.TCPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        try:
            class ReusableTCPServer(socketserver.TCPServer):
                allow_reuse_address = True

            self._server = ReusableTCPServer(("0.0.0.0", self.port), CaptiveHTTPHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="CaptiveHTTP")
            self._thread.start()
            logger.info("[Portal HTTP] Listening on port :%d", self.port)
            return True
        except OSError as e:
            logger.debug("[Portal HTTP] Unable to bind port :%d: %s", self.port, e)
            return False

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


# ── Subsystem Helpers (DHCP Option 114, iptables, hosts) ──────────────────────
def setup_nm_capport_config(gateway_ip: str = DEFAULT_GATEWAY_IP, http_port: int = DEFAULT_HTTP_PORT) -> bool:
    import sys
    target_mod = sys.modules.get("src.devices.wifi.portal_capport", sys.modules[__name__])
    dir_path = getattr(target_mod, "NM_DNSMASQ_DIR", NM_DNSMASQ_DIR)
    file_path = getattr(target_mod, "NM_CAPPORT_FILE", NM_CAPPORT_FILE)
    try:
        p_sfx = f":{http_port}" if http_port != 80 else ""
        content = f"address=/#/{gateway_ip}\ndhcp-option=114,http://{gateway_ip}{p_sfx}/.well-known/captive-portal\n"
        if file_path.exists() and file_path.read_text(encoding="utf-8") == content:
            return True
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return True
        except (OSError, PermissionError):
            pass
        pfx = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and shutil.which("sudo") else []
        subprocess.run(pfx + ["mkdir", "-p", str(dir_path)], check=False)
        cmd = pfx + ["tee", str(file_path)]
        proc = subprocess.run(cmd, input=content.encode("utf-8"), capture_output=True, check=False)
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def teardown_nm_capport_config() -> None:
    import sys
    target_mod = sys.modules.get("src.devices.wifi.portal_capport", sys.modules[__name__])
    file_path = getattr(target_mod, "NM_CAPPORT_FILE", NM_CAPPORT_FILE)
    try:
        if file_path.exists():
            try:
                file_path.unlink(missing_ok=True)
                return
            except (OSError, PermissionError):
                pass
            pfx = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and shutil.which("sudo") else []
            subprocess.run(pfx + ["rm", "-f", str(file_path)], check=False)
    except (subprocess.SubprocessError, OSError):
        pass


def setup_port_forwarding(iface: str = "wlan0", http_port: int = DEFAULT_HTTP_PORT, dns_port: int = DEFAULT_DNS_PORT) -> bool:
    return True  # Managed through native routing


def teardown_port_forwarding(iface: str = "wlan0", http_port: int = DEFAULT_HTTP_PORT, dns_port: int = DEFAULT_DNS_PORT) -> None:
    pass


def ensure_local_domain(domain: str = "hermes.local", ips: tuple[str, ...] = ("127.0.0.1", "10.42.0.1"), hosts_path: Path = DEFAULT_HOSTS) -> bool:
    try:
        if not hosts_path.exists() or not hosts_path.is_file():
            return False
        content = hosts_path.read_text(encoding="utf-8")
        needed = [f"{ip}\t{domain}" for ip in ips if f"{ip}\t{domain}" not in content and f"{ip} {domain}" not in content]
        if not needed:
            return True
        lines = [line for line in content.splitlines() if line.strip()]
        lines.extend(needed)
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        try:
            hosts_path.write_bytes(payload)
        except PermissionError:
            res = subprocess.run(["sudo", "-n", "tee", str(hosts_path)], input=payload, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if res.returncode != 0:
                raise
        return True
    except (OSError, PermissionError):
        return False


# ── Coordinated Captive Portal Service ─────────────────────────────────────────
class CaptivePortalService:
    """Coordinates DNS interception, HTTP captive server, and Option 114 config."""

    def __init__(self) -> None:
        self.dns_server = CaptiveDNSServer()
        self.http_server = CaptiveHTTPServer()
        self.is_active = False

    def start(self, ip: str = DEFAULT_GATEWAY_IP, iface: str = "wlan0") -> bool:
        if self.is_active:
            return True
        setup_nm_capport_config(gateway_ip=ip)
        self.dns_server.ip = ip
        dns_ok = self.dns_server.start()
        http_ok = self.http_server.start()
        self.is_active = bool(dns_ok or http_ok)
        logger.info("[Portal Service] Captive portal active on %s (DNS=%s, HTTP=%s)", ip, dns_ok, http_ok)
        return self.is_active

    def stop(self) -> None:
        self.http_server.stop()
        self.dns_server.stop()
        teardown_nm_capport_config()
        self.is_active = False
        logger.info("[Portal Service] Captive portal stopped.")


portal_service = CaptivePortalService()
