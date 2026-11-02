"""test_wifi_hotspot.py — Unit tests for nmcli hotspot AP and watchdog lifecycle."""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from src.devices.wifi import activity, hotspot, runner, watchdog


class TestWiFiHotspot(unittest.TestCase):
    def setUp(self) -> None:
        activity._suspended_until = 0.0
        runner.SIMULATION_STATE["enabled"], runner.SIMULATION_STATE["hotspot_active"] = True, False

    def tearDown(self) -> None:
        watchdog.stop_wifi_watchdog(); hotspot.stop_hotspot()

    def test_hotspot_lifecycle_simulated(self) -> None:
        self.assertFalse(hotspot.is_hotspot_active())
        self.assertTrue(hotspot.start_hotspot("hermes", "12345678"))
        self.assertTrue(hotspot.is_hotspot_active())
        self.assertTrue(hotspot.stop_hotspot()); self.assertTrue(hotspot.stop_hotspot())
        self.assertFalse(hotspot.is_hotspot_active())

    @patch("src.devices.wifi.portal_service.portal_service.start", return_value=True)
    @patch("src.devices.wifi.portal_service.portal_service.stop", return_value=None)
    def test_emergency_hotspot_lifecycle(self, mock_stop: MagicMock, mock_start: MagicMock) -> None:
        self.assertTrue(hotspot.start_emergency_hotspot("hermes", "12345678"))
        self.assertTrue(hotspot.is_hotspot_active())
        self.assertTrue(hotspot.stop_emergency_hotspot()); self.assertTrue(hotspot.stop_emergency_hotspot())
        self.assertFalse(hotspot.is_hotspot_active())

    def test_watchdog_suspension_and_lifecycle(self) -> None:
        activity.suspend_watchdog(1.0); self.assertTrue(activity.is_watchdog_suspended())
        self.assertTrue(watchdog.start_wifi_watchdog(interval=0.1)); self.assertTrue(watchdog.is_watchdog_running())
        watchdog.stop_wifi_watchdog(); self.assertFalse(watchdog.is_watchdog_running())

    @patch("src.devices.led.led_controller.set_network_status")
    @patch("src.core.stability.scale_state_machine.set_network_status")
    def test_notify_network_status(self, mock_scale: MagicMock, mock_led: MagicMock) -> None:
        watchdog.notify_network_status(False)
        mock_led.assert_called_with(False); mock_scale.assert_called_with(False)
        watchdog.notify_network_status(True)
        mock_led.assert_called_with(True); mock_scale.assert_called_with(True)

    @patch("src.devices.wifi.watchdog.notify_network_status")
    @patch("src.devices.wifi.watchdog.is_network_connected", side_effect=[False, False, False, False])
    def test_watchdog_loop_notifies_status(self, mock_conn: MagicMock, mock_notify: MagicMock) -> None:
        watchdog.start_wifi_watchdog(interval=0.01); time.sleep(0.08); watchdog.stop_wifi_watchdog()
        mock_notify.assert_any_call(False)


if __name__ == "__main__":
    unittest.main()
