"""test_wifi_manager.py — Unit tests for balena-based Wi-Fi management in Hermes."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.devices.wifi import (
    connect_to_wifi,
    get_available_networks,
    get_existing_profile,
    get_target_arch,
    get_wifi_interface,
    has_hotspot_connected,
    is_balena_available,
    is_hotspot_active,
    is_network_connected,
    is_nmcli_available,
    is_wifi_connected,
    start_emergency_hotspot,
    start_wifi_watchdog,
    stop_emergency_hotspot,
    stop_wifi_watchdog,
)
from src.devices.wifi.process import balena_manager


class TestWiFiManager(unittest.TestCase):
    def tearDown(self) -> None:
        stop_wifi_watchdog()
        stop_emergency_hotspot()

    @patch("socket.create_connection")
    def test_is_wifi_connected_true(self, mock_conn: MagicMock) -> None:
        mock_conn.return_value.__enter__.return_value = MagicMock()
        self.assertTrue(is_wifi_connected())
        self.assertTrue(is_network_connected())

    @patch("socket.create_connection", side_effect=OSError("Unreachable"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_is_wifi_connected_false_when_disconnected(self, mock_exists: MagicMock, mock_conn: MagicMock) -> None:
        self.assertFalse(is_wifi_connected())

    def test_start_and_stop_emergency_hotspot(self) -> None:
        with patch.object(balena_manager, "start_portal", return_value=True) as mock_start, \
             patch.object(balena_manager, "stop_portal", return_value=True) as mock_stop:
            started = start_emergency_hotspot("hermes", "12345678")
            self.assertTrue(started)
            mock_start.assert_called_once()

            stopped = stop_emergency_hotspot()
            self.assertTrue(stopped)
            mock_stop.assert_called_once()

    def test_is_hotspot_active(self) -> None:
        with patch.object(balena_manager, "is_running", return_value=True):
            self.assertTrue(is_hotspot_active())
        with patch.object(balena_manager, "is_running", return_value=False):
            self.assertFalse(is_hotspot_active())

    def test_connect_to_wifi_empty_ssid(self) -> None:
        ok, msg = connect_to_wifi("", "password")
        self.assertFalse(ok)
        self.assertIn("cannot be empty", msg)

    @patch("src.devices.wifi.connection.save_wifi_network")
    @patch("src.devices.wifi.connection.is_network_connected", return_value=True)
    @patch("src.devices.wifi.connection.submit_credentials", return_value=(True, "OK"))
    def test_connect_to_wifi_success(self, mock_submit: MagicMock, mock_online: MagicMock, mock_save: MagicMock) -> None:
        ok, msg = connect_to_wifi("Office_5G", "secret123")
        self.assertTrue(ok)
        self.assertIn("Successfully connected", msg)
        mock_save.assert_called_once_with("Office_5G", "secret123")

    @patch("src.devices.wifi.connection.start_emergency_hotspot")
    @patch("src.devices.wifi.connection.is_hotspot_active", return_value=False)
    @patch("src.devices.wifi.connection.submit_credentials", return_value=(False, "Rejected"))
    def test_connect_to_wifi_failure_restores_hotspot(
        self, mock_submit: MagicMock, mock_active: MagicMock, mock_hotspot: MagicMock
    ) -> None:
        ok, msg = connect_to_wifi("BadSSID", "wrongpass")
        self.assertFalse(ok)
        self.assertIn("Rejected", msg)
        mock_hotspot.assert_called_once()

    def test_get_available_networks(self) -> None:
        networks = get_available_networks()
        self.assertIsInstance(networks, list)
        self.assertTrue(len(networks) > 0)
        self.assertIn("ssid", networks[0])

    @patch("pathlib.Path.is_dir", return_value=False)
    def test_get_wifi_interface_fallback(self, mock_isdir: MagicMock) -> None:
        self.assertEqual(get_wifi_interface(), "wlan0")

    def test_target_arch_mapping(self) -> None:
        with patch("platform.machine", return_value="aarch64"):
            self.assertEqual(get_target_arch(), "linux-aarch64")
        with patch("platform.machine", return_value="x86_64"):
            self.assertEqual(get_target_arch(), "linux-amd64")
        with patch("platform.machine", return_value="armv7l"):
            self.assertEqual(get_target_arch(), "linux-armv7hf")
        with patch("platform.machine", return_value="unknown"):
            self.assertIsNone(get_target_arch())

    @patch("src.core.wifi_vault.get_wifi_password")
    def test_get_existing_profile(self, mock_pwd: MagicMock) -> None:
        mock_pwd.return_value = "pass123"
        self.assertEqual(get_existing_profile("KnownSSID"), "KnownSSID")
        mock_pwd.return_value = None
        self.assertIsNone(get_existing_profile("UnknownSSID"))

    def test_watchdog_lifecycle(self) -> None:
        start_wifi_watchdog(interval=0.1)
        stop_wifi_watchdog()

    def test_availability_flags(self) -> None:
        self.assertIsInstance(is_balena_available(), bool)
        self.assertIsInstance(is_nmcli_available(), bool)

    @patch("src.devices.wifi.cmd_builder.build_portal_cmd", return_value=None)
    def test_start_portal_fails_when_binary_missing(self, mock_cmd: MagicMock) -> None:
        with patch.object(balena_manager, "is_running", return_value=False):
            result = balena_manager.start_portal("hermes", "12345678")
            self.assertFalse(result)

    @patch("src.devices.wifi.cmd_builder.build_portal_cmd", return_value=["wifi-connect"])
    @patch("src.devices.wifi.cmd_builder.spawn_portal_process", return_value=None)
    def test_start_portal_fails_when_spawn_fails(self, mock_spawn: MagicMock, mock_cmd: MagicMock) -> None:
        with patch.object(balena_manager, "is_running", return_value=False):
            result = balena_manager.start_portal("hermes", "12345678")
            self.assertFalse(result)

    def test_balena_binary_names_includes_scripts_bin(self) -> None:
        from src.devices.wifi.constants import BALENA_BINARY_NAMES
        found = any("scripts/bin/wifi-connect" in name for name in BALENA_BINARY_NAMES)
        self.assertTrue(found)

    def test_balena_has_connected_detection(self) -> None:
        with patch.object(balena_manager, "has_connected", return_value=True):
            self.assertTrue(has_hotspot_connected())
        with patch.object(balena_manager, "has_connected", return_value=False):
            self.assertFalse(has_hotspot_connected())

    def test_balena_process_manager_poll_code_zero(self) -> None:
        proc_mock = MagicMock()
        proc_mock.poll.return_value = 0
        with patch("src.devices.wifi.process.is_balena_available", return_value=True):
            balena_manager._process = proc_mock
            self.assertTrue(balena_manager.has_connected())
            self.assertFalse(balena_manager.is_running())
            balena_manager._process = None

    @patch("src.devices.wifi.watchdog.hs.is_hotspot_active")
    @patch("src.devices.wifi.watchdog.cty.is_network_connected")
    def test_watchdog_does_not_probe_network_when_hotspot_active(
        self, mock_net: MagicMock, mock_hotspot: MagicMock
    ) -> None:
        from src.devices.wifi.watchdog import _loop, _stop_event

        def stop_after_active() -> bool:
            _stop_event.set()
            return True

        mock_hotspot.side_effect = stop_after_active
        _stop_event.clear()
        _loop(interval=0.01)
        mock_net.assert_not_called()

    @patch("src.devices.wifi.watchdog.hs.get_hotspot_exit_details", return_value=(17, "Address in use"))
    @patch("src.devices.wifi.watchdog.hs.stop_emergency_hotspot")
    @patch("src.devices.wifi.watchdog.hs.is_hotspot_active", return_value=False)
    @patch("src.devices.wifi.watchdog.hs.has_hotspot_connected", return_value=False)
    def test_watchdog_cleans_up_on_error_exit_code(
        self, mock_connected: MagicMock, mock_active: MagicMock, mock_stop: MagicMock, mock_details: MagicMock
    ) -> None:
        from src.devices.wifi.watchdog import _loop, _stop_event

        def stop_after_cleanup() -> bool:
            _stop_event.set()
            return False

        mock_active.side_effect = stop_after_cleanup
        _stop_event.clear()
        _loop(interval=0.01)
        mock_stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
