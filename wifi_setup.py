"""wifi_setup.py — Standalone CLI entry point for balena Wi-Fi setup in Hermes."""
from __future__ import annotations

import argparse
import signal
import sys
import time

from src.devices.wifi import (
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    connect_to_wifi,
    install_wifi_connect,
    is_balena_available,
    start_emergency_hotspot,
    start_wifi_watchdog,
    stop_emergency_hotspot,
    stop_wifi_watchdog,
)


def _shutdown(signum: int = 0, frame: object = None) -> None:
    stop_wifi_watchdog()
    stop_emergency_hotspot()
    sys.exit(0)


def main() -> None:
    p = argparse.ArgumentParser(description="Hermes Balena Wi-Fi Setup")
    p.add_argument("--connect", action="store_true", help="Connect to Wi-Fi")
    p.add_argument("--ssid", default=DEFAULT_HOTSPOT_SSID, help="Target SSID")
    p.add_argument("--password", default=DEFAULT_HOTSPOT_PASS, help="Password")
    p.add_argument("--install", action="store_true", help="Download wifi-connect")
    args = p.parse_args()

    if args.install:
        print(f"[Balena WiFi] Installed to: {install_wifi_connect()}")
        return

    if args.connect:
        ssid = args.ssid if args.ssid != DEFAULT_HOTSPOT_SSID else input("SSID: ")
        pwd = args.password if args.password != DEFAULT_HOTSPOT_PASS else input("Password: ")
        ok, msg = connect_to_wifi(ssid, pwd)
        print(f"[{'SUCCESS' if ok else 'FAILED'}] {msg}")
        return

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if not is_balena_available() and sys.platform.startswith("linux"):
        try:
            install_wifi_connect()
        except (OSError, RuntimeError) as e:
            print(f"[Balena WiFi] Auto-download note: {e}")

    start_emergency_hotspot(ssid=args.ssid, password=args.password)
    start_wifi_watchdog()
    print(f"[Balena WiFi] Hotspot active (SSID: {args.ssid}). Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()
