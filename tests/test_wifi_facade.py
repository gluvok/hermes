"""Verify consolidated Wi-Fi package preserves all public API signatures."""
import unittest
from src.devices.wifi import (
    is_wifi_connected,
    is_network_connected,
    scan_networks,
    connect_to_wifi,
    start_emergency_hotspot,
    stop_emergency_hotspot,
    start_wifi_watchdog,
    stop_wifi_watchdog,
    is_hotspot_active,
)

class TestWiFiFacade(unittest.TestCase):
    def test_public_interface_exists(self):
        self.assertTrue(callable(is_wifi_connected))
        self.assertTrue(callable(is_network_connected))
        self.assertTrue(callable(scan_networks))
        self.assertTrue(callable(connect_to_wifi))
        self.assertTrue(callable(start_emergency_hotspot))
        self.assertTrue(callable(stop_emergency_hotspot))
        self.assertTrue(callable(start_wifi_watchdog))
        self.assertTrue(callable(stop_wifi_watchdog))
        self.assertTrue(callable(is_hotspot_active))
