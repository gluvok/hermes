from __future__ import annotations

import unittest
from unittest.mock import patch

from src.web.app import create_app


class TestEmergencyHotspotFlow(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})
        self.client = self.app.test_client()

    def test_captive_portal_probe_redirects_when_offline(self):
        with patch("src.web.blueprints.views.is_wifi_connected", return_value=False):
            # Apple CNA probe
            res_apple = self.client.get("/hotspot-detect.html")
            self.assertEqual(res_apple.status_code, 302)
            self.assertIn("/wifi", res_apple.headers.get("Location", ""))

            # Android 204 probe
            res_android = self.client.get("/generate_204")
            self.assertEqual(res_android.status_code, 302)
            self.assertIn("/wifi", res_android.headers.get("Location", ""))

            # Windows NCSI probe
            res_win = self.client.get("/ncsi.txt")
            self.assertEqual(res_win.status_code, 302)

            # Modern RFC 8908 CAPPORT probe
            res_capport = self.client.get("/.well-known/captive-portal")
            self.assertEqual(res_capport.status_code, 200)
            data = res_capport.get_json()
            self.assertTrue(data.get("captive"))
            self.assertEqual(data.get("user-portal-url"), "/wifi")

    def test_captive_portal_probe_returns_204_when_online(self):
        with patch("src.web.blueprints.views.is_wifi_connected", return_value=True):
            res_android = self.client.get("/generate_204")
            self.assertEqual(res_android.status_code, 204)

            res_capport = self.client.get("/.well-known/captive-portal")
            self.assertEqual(res_capport.status_code, 200)
            data = res_capport.get_json()
            self.assertFalse(data.get("captive"))

    def test_hermes_config_domain_redirects_to_config(self):
        res = self.client.get("/", headers={"Host": "hermes.config"})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/config")
