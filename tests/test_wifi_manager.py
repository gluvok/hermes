"""test_wifi_manager.py — Unit tests for pure nmcli Wi-Fi management in Hermes."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.devices.wifi import manager

connection = manager
connectivity = manager
runner = manager
scanner = manager


class TestWiFiManager(unittest.TestCase):
    def setUp(self) -> None:
        runner.SIMULATION_STATE["enabled"] = True
        runner.SIMULATION_STATE["active_ssid"] = ""

    @patch("socket.create_connection")
    def test_is_wifi_connected_true(self, mock_conn: MagicMock) -> None:
        mock_conn.return_value.__enter__.return_value = MagicMock()
        self.assertTrue(connectivity.is_wifi_connected())
        self.assertTrue(connectivity.is_network_connected())

    @patch("socket.create_connection", side_effect=OSError("Unreachable"))
    def test_is_wifi_connected_false(self, mock_conn: MagicMock) -> None:
        self.assertFalse(connectivity.is_wifi_connected())

    def test_connect_to_wifi_empty_ssid(self) -> None:
        ok, msg = connection.connect_to_wifi("", "password")
        self.assertFalse(ok)
        self.assertIn("cannot be empty", msg)

    @patch("src.devices.wifi.connection.save_wifi_network")
    def test_connect_to_wifi_simulated(self, mock_save: MagicMock) -> None:
        ok, msg = connection.connect_to_wifi("Office_5G", "secret123")
        self.assertTrue(ok)
        self.assertIn("Connected", msg)
        self.assertEqual(connection.get_active_wifi_ssid(), "Office_5G")
        mock_save.assert_called_once()

    def test_scan_and_available_networks(self) -> None:
        nets = scanner.get_available_networks()
        self.assertIsInstance(nets, list)
        self.assertTrue(len(nets) > 0)
        self.assertIn("ssid", nets[0])
        self.assertEqual(scanner.scan_networks(), nets)

    @patch("pathlib.Path.is_dir", return_value=False)
    def test_get_wifi_interface_fallback(self, mock_isdir: MagicMock) -> None:
        self.assertEqual(runner.get_wifi_interface(), "wlan0")

    def test_availability_flags(self) -> None:
        self.assertIsInstance(runner.is_nmcli_available(), bool)
        self.assertTrue(connection.get_existing_profile("AnySSID"))


if __name__ == "__main__":
    unittest.main()
