"""test_wifi_portal.py — Unit tests for captive DNS, HTTP endpoints, and probe redirects."""
from __future__ import annotations

import json
import socket
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.devices.wifi.portal_dns import _build_response
from src.devices.wifi.portal_hosts import ensure_local_domain
from src.devices.wifi.portal_http import CaptiveHTTPServer
from src.devices.wifi.runner import SIMULATION_STATE


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: object, code: int, msg: str, headers: object, newurl: str) -> None: return None


class TestWiFiPortal(unittest.TestCase):
    def setUp(self) -> None: SIMULATION_STATE["enabled"] = True


    def test_dns_packet_builder(self) -> None:
        dummy_a = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01"
        resp_a = _build_response(dummy_a, "10.42.0.1")
        self.assertEqual(resp_a[:2], b"\x12\x34"); self.assertTrue(resp_a.endswith(socket.inet_aton("10.42.0.1")))
        dummy_aaaa = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x1c\x00\x01"
        self.assertEqual(len(_build_response(dummy_aaaa, "10.42.0.1")), 29)

    def test_portal_http_endpoints_and_probes(self) -> None:
        http_srv = CaptiveHTTPServer(port=8894)
        self.assertTrue(http_srv.start())
        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            base = f"http://127.0.0.1:{http_srv.port}"
            with urllib.request.urlopen(f"{base}/", timeout=3.0) as r:
                self.assertEqual(r.status, 200); self.assertIn("Gluvok Hermes", r.read().decode())
            with urllib.request.urlopen(f"{base}/networks", timeout=3.0) as r:
                self.assertEqual(r.status, 200); self.assertIsInstance(json.loads(r.read().decode()), list)
            req = urllib.request.Request(f"{base}/generate_204", headers={"Host": "connectivitycheck.gstatic.com"})
            try: opener.open(req, timeout=3.0)
            except urllib.error.HTTPError as e: self.assertEqual(e.code, 302)
            try: opener.open(urllib.request.Request(f"{base}/config"), timeout=3.0)
            except urllib.error.HTTPError as e: self.assertEqual(e.code, 302); self.assertIn("8080/config", e.headers.get("Location", ""))
        finally: http_srv.stop()

    def test_ensure_local_domain(self) -> None:
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("127.0.0.1 localhost\n"); p = Path(f.name)
        try:
            self.assertTrue(ensure_local_domain("hermes.local", ("127.0.0.1", "10.42.0.1"), hosts_path=p))
            self.assertIn("127.0.0.1\thermes.local", p.read_text())
        finally: p.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()

