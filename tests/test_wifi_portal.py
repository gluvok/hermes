"""test_wifi_portal.py — Unit tests for captive DNS, HTTP endpoints, and probe redirects."""
from __future__ import annotations

import json
import socket
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.devices.wifi.portal_dns import _build_response
from src.devices.wifi.portal_hosts import ensure_local_domain
from src.devices.wifi.portal_http import CaptiveHTTPServer
from src.devices.wifi.runner import SIMULATION_STATE
from src.web import auth


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
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler)
        try:
            base = f"http://127.0.0.1:{http_srv.port}"
            with opener.open(f"{base}/", timeout=3.0) as r:
                self.assertEqual(r.status, 200); self.assertIn("Gluvok Hermes", r.read().decode())
            with opener.open(f"{base}/networks", timeout=3.0) as r:
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

class TestPortalConnectAuth(unittest.TestCase):
    """#32: /connect needs admin credentials, bounded bodies, and /saved is gone."""

    def setUp(self) -> None:
        SIMULATION_STATE["enabled"] = True
        auth._failed_login_attempts.clear()
        self.addCleanup(auth._failed_login_attempts.clear)
        self.srv = CaptiveHTTPServer(port=8895)
        self.assertTrue(self.srv.start())
        self.addCleanup(self.srv.stop)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler)
        self.base = f"http://127.0.0.1:{self.srv.port}"

    def _post(self, body: bytes) -> tuple[int, dict]:
        req = urllib.request.Request(f"{self.base}/connect", data=body, method="POST", headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=3.0) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    @staticmethod
    def _creds(**extra: str) -> bytes:
        return json.dumps({"ssid": "Office", "password": "pw", "userid": "superadmin", "admin_password": "test-admin-pass", **extra}).encode()

    @patch("src.devices.wifi.portal_handlers.connect_to_wifi")
    def test_connect_without_credentials_is_401(self, mock_connect: MagicMock) -> None:
        status, _ = self._post(json.dumps({"ssid": "Office", "password": "pw"}).encode())
        self.assertEqual(status, 401)
        mock_connect.assert_not_called()

    @patch("src.devices.wifi.portal_handlers.connect_to_wifi")
    def test_connect_with_wrong_password_is_401(self, mock_connect: MagicMock) -> None:
        status, _ = self._post(self._creds(admin_password="nope"))
        self.assertEqual(status, 401)
        mock_connect.assert_not_called()

    @patch("src.devices.wifi.portal_handlers.connect_to_wifi", return_value=(True, "ok"))
    def test_connect_with_credentials_connects(self, mock_connect: MagicMock) -> None:
        status, body = self._post(self._creds())
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        mock_connect.assert_called_once_with("Office", "pw")

    @patch("src.devices.wifi.portal_handlers.connect_to_wifi")
    def test_connect_is_rate_limited_after_failures(self, mock_connect: MagicMock) -> None:
        for _ in range(auth.MAX_FAILED_LOGIN_ATTEMPTS):
            self.assertEqual(self._post(b"{}")[0], 401)
        self.assertEqual(self._post(self._creds())[0], 429)
        mock_connect.assert_not_called()

    @patch("src.devices.wifi.portal_handlers.connect_to_wifi")
    def test_connect_oversized_body_is_413(self, mock_connect: MagicMock) -> None:
        status, _ = self._post(self._creds(padding="x" * 5000))
        self.assertEqual(status, 413)
        mock_connect.assert_not_called()

    @patch("src.devices.wifi.portal_handlers.connect_to_wifi")
    def test_connect_non_object_json_is_401_not_500(self, mock_connect: MagicMock) -> None:
        self.assertEqual(self._post(b"[1, 2]")[0], 401)
        mock_connect.assert_not_called()

    def test_saved_no_longer_serves_json(self) -> None:
        with self.opener.open(f"{self.base}/saved", timeout=3.0) as r:
            self.assertIn("text/html", r.headers.get("Content-Type", ""))


if __name__ == "__main__":
    unittest.main()

