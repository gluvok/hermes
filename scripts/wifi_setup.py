"""wifi_setup.py — Standalone CLI entry point for nmcli Wi-Fi setup in Hermes."""
from __future__ import annotations

import argparse
import signal
import sys
import time

from src.devices.wifi import (
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    connect_to_wifi,
    is_network_connected,
    scan_networks,
    start_emergency_hotspot,
    start_wifi_watchdog,
    stop_emergency_hotspot,
    stop_wifi_watchdog,
)


def _shutdown(signum: int = 0, frame: object = None) -> None:
    print("\n[WiFi Setup] Shutting down watchdog and captive portal...")
    stop_wifi_watchdog(); stop_emergency_hotspot(); sys.exit(0)


def main() -> None:
    p = argparse.ArgumentParser(description="Hermes nmcli Wi-Fi Setup & Watchdog")
    p.add_argument("--scan", action="store_true", help="Scan nearby Wi-Fi networks")
    p.add_argument("--connect", action="store_true", help="Connect to Wi-Fi")
    p.add_argument("--ssid", default="", help="Target network SSID")
    p.add_argument("--password", default="", help="Network password")
    p.add_argument("--hotspot", action="store_true", help="Manually activate emergency hotspot")
    args = p.parse_args()

    if args.scan:
        for net in scan_networks(): print(f"- {net['ssid']} ({net.get('signal', 0)}%) [{net.get('security', 'Open')}]")
        return
    if args.connect:
        ok, msg = connect_to_wifi(args.ssid or input("SSID: "), args.password or input("Password: "))
        print(f"[{'SUCCESS' if ok else 'FAILED'}] {msg}"); return

    signal.signal(signal.SIGINT, _shutdown); signal.signal(signal.SIGTERM, _shutdown)
    ssid, pwd = args.ssid or DEFAULT_HOTSPOT_SSID, args.password or DEFAULT_HOTSPOT_PASS

    if args.hotspot or not is_network_connected():
        print(f"[WiFi Setup] Initiating emergency hotspot '{ssid}'...")
        if start_emergency_hotspot(ssid, pwd):
            print(f"[WiFi Setup] Hotspot active (SSID: {ssid}, Password: {pwd}) at http://hermes.local or http://10.42.0.1")

    start_wifi_watchdog()
    print("[WiFi Setup] Watchdog active. Monitoring connectivity...")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: _shutdown()


if __name__ == "__main__":
    main()
