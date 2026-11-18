"""test_wifi_capport.py — Unit tests for NetworkManager dnsmasq capport config."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.devices.wifi import portal as portal_capport


class TestWiFiCapport(unittest.TestCase):
    def test_setup_and_teardown_capport_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            conf_dir = Path(td)
            conf_file = conf_dir / "hermes-captive.conf"
            with (
                patch.object(portal_capport, "NM_DNSMASQ_DIR", conf_dir),
                patch.object(portal_capport, "NM_CAPPORT_FILE", conf_file),
            ):
                self.assertTrue(portal_capport.setup_nm_capport_config("10.42.0.1"))
                self.assertTrue(conf_file.exists())
                content = conf_file.read_text(encoding="utf-8")
                self.assertIn("address=/#/10.42.0.1", content)
                self.assertIn(
                    "dhcp-option=114,http://10.42.0.1/.well-known/captive-portal",
                    content,
                )
                self.assertNotIn("address=/=/", content)
                # Second call is idempotent
                self.assertTrue(portal_capport.setup_nm_capport_config("10.42.0.1"))
                # Teardown removes file
                portal_capport.teardown_nm_capport_config()
                self.assertFalse(conf_file.exists())


if __name__ == "__main__":
    unittest.main()
