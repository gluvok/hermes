"""portal_dns.py — Intercepts all DNS queries and resolves them to portal IP."""
from __future__ import annotations

import logging
import socket
import threading

from src.devices.wifi.constants import DEFAULT_DNS_PORT, DEFAULT_GATEWAY_IP

logger = logging.getLogger(__name__)


def _build_response(data: bytes, ip: str) -> bytes:
    tid, qend = data[:2], data.find(b"\x00", 12) + 5
    if qend < 17 or len(data) < qend: return b""
    qtype, question = int.from_bytes(data[qend-4:qend-2], "big"), data[12:qend]
    if qtype in (1, 255):
        ans = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + socket.inet_aton(ip)
        return tid + b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00" + question + ans
    return tid + b"\x81\x80\x00\x01\x00\x00\x00\x00\x00\x00" + question


class CaptiveDNSServer:
    """Lightweight UDP DNS resolver redirecting all queries to captive portal."""

    def __init__(self, ip: str = DEFAULT_GATEWAY_IP, port: int = DEFAULT_DNS_PORT) -> None:
        self.ip, self.port = ip, port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> bool:
        if self._running: return True
        for p in (53, self.port):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", p))
                self._sock, self.port, self._running = s, p, True; break
            except (OSError, PermissionError): continue
        if not self._sock: return False
        self._thread = threading.Thread(target=self._serve, name="CaptiveDNS", daemon=True)
        self._thread.start()
        logger.info("[DNS] Captive DNS responder active on UDP :%d (queries -> %s)", self.port, self.ip)
        return True

    def _serve(self) -> None:
        while self._running and self._sock:
            try:
                data, addr = self._sock.recvfrom(512)
                resp = _build_response(data, self.ip)
                if resp: self._sock.sendto(resp, addr)
            except OSError: break

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try: self._sock.close()
            except OSError: pass
            self._sock = None
