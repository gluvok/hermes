"""Verify consolidated Wi-Fi package preserves all public API signatures."""

import unittest

from src.devices.wifi import (
    connect_to_wifi,
    is_hotspot_active,
    is_network_connected,
    is_wifi_connected,
    scan_networks,
    start_emergency_hotspot,
    start_wifi_watchdog,
    stop_emergency_hotspot,
    stop_wifi_watchdog,
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
