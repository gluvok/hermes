"""test_wifi_manager.py — Unit tests for pure nmcli Wi-Fi management in Hermes."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.devices.wifi import connection, connectivity, runner, scanner


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

    def test_is_network_connected_probes_cloud_host_first(self) -> None:
        attempted: list[tuple[str, int]] = []

        def fake_conn(addr: tuple[str, int], timeout: float = 1.5) -> MagicMock:
            attempted.append(addr)
            if addr == ("staging.example.com", 8443):
                return MagicMock()
            raise OSError("DNS blocked")

        with (
            patch("src.config.constants.GLUVOK_BASE_URL", "https://staging.example.com:8443"),
            patch("socket.create_connection", side_effect=fake_conn),
        ):
            self.assertTrue(connectivity.is_network_connected())

        self.assertEqual(attempted, [("staging.example.com", 8443)])

    def test_is_network_connected_falls_back_to_dns_when_cloud_unreachable(self) -> None:
        attempted: list[tuple[str, int]] = []

        def fake_conn(addr: tuple[str, int], timeout: float = 1.5) -> MagicMock:
            attempted.append(addr)
            if addr == ("1.1.1.1", 53):
                return MagicMock()
            raise OSError("Cloud down")

        with (
            patch("src.config.constants.GLUVOK_BASE_URL", "https://gluvok.vercel.app"),
            patch("socket.create_connection", side_effect=fake_conn),
        ):
            self.assertTrue(connectivity.is_network_connected())

        self.assertEqual(attempted, [("gluvok.vercel.app", 443), ("1.1.1.1", 53)])

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


class TestConnectWifiHardening(unittest.TestCase):
    """#32: connect_wifi must validate the SSID and never delete AP/foreign profiles."""

    def setUp(self) -> None:
        runner.SIMULATION_STATE["enabled"] = False
        patches = [
            patch("src.devices.wifi.runner.is_nmcli_available", return_value=True),
            patch("src.devices.wifi.runner.get_wifi_interface", return_value="wlan0"),
            patch("src.devices.wifi.connection.suspend_watchdog"),
            patch("src.devices.wifi.connection.hotspot.stop_hotspot"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(runner.SIMULATION_STATE.__setitem__, "enabled", True)

    @staticmethod
    def _calls(mock_nmcli: MagicMock) -> list[list[str]]:
        return [c.args[0] for c in mock_nmcli.call_args_list]

    @patch("src.devices.wifi.runner.run_nmcli")
    def test_connect_wifi_rejects_bad_ssid_without_nmcli(self, mock_nmcli: MagicMock) -> None:
        for bad in ("-x", "a" * 33, "é" * 17):
            ok, msg = connection.connect_wifi(bad)
            self.assertFalse(ok, bad)
            self.assertIn("Invalid SSID", msg)
        mock_nmcli.assert_not_called()

    @patch("src.devices.wifi.runner.run_nmcli")
    def test_connect_wifi_never_deletes_hotspot_profile(self, mock_nmcli: MagicMock) -> None:
        def fake(args: list[str], **_: object) -> tuple[int, str]:
            if args[0] == "-g":
                return 0, "802-11-wireless\nhermes\nap"
            return 0, "ok"

        mock_nmcli.side_effect = fake
        connection.connect_wifi("hermes-hotspot", "pw")
        self.assertFalse(any(c[:2] == ["connection", "delete"] for c in self._calls(mock_nmcli)))

    @patch("src.devices.wifi.runner.run_nmcli")
    def test_connect_wifi_deletes_own_client_profile(self, mock_nmcli: MagicMock) -> None:
        def fake(args: list[str], **_: object) -> tuple[int, str]:
            if args[0] == "-g":
                return 0, "802-11-wireless\nOffice\ninfrastructure"
            return 0, "ok"

        mock_nmcli.side_effect = fake
        ok, _ = connection.connect_wifi("Office", "pw")
        self.assertTrue(ok)
        self.assertIn(["connection", "delete", "id", "Office"], self._calls(mock_nmcli))

    @patch("src.devices.wifi.runner.run_nmcli")
    def test_is_client_profile_handles_escaped_colon_and_empty_mode(self, mock_nmcli: MagicMock) -> None:
        # nmcli -g prints one value per line and escapes ':' as '\:'; an unset mode prints an
        # empty line that run_nmcli's strip() removes.
        mock_nmcli.return_value = (0, "802-11-wireless\nCafe\\: Guest")
        self.assertTrue(connection._is_client_profile_for("Cafe: Guest"))
        mock_nmcli.return_value = (0, "802-3-ethernet\n\n")
        self.assertFalse(connection._is_client_profile_for("eth"))
        mock_nmcli.return_value = (10, "Error: unknown connection")
        self.assertFalse(connection._is_client_profile_for("gone"))


if __name__ == "__main__":
    unittest.main()
