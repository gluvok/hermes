"""connection.py — Connects device to facility Wi-Fi networks via nmcli."""
from __future__ import annotations

import logging
import sqlite3

from src.core.wifi_vault import save_wifi_network
from src.devices.wifi import hotspot, runner
from src.devices.wifi.activity import suspend_watchdog

logger = logging.getLogger(__name__)


def get_active_wifi_ssid(iface: str | None = None) -> str | None:
    if not runner.is_nmcli_available() or runner.SIMULATION_STATE["enabled"]:
        return str(runner.SIMULATION_STATE.get("active_ssid", ""))
    dev = iface or runner.get_wifi_interface()
    code, out = runner.run_nmcli(["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    if code != 0: return None
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1].strip() == dev and not parts[0].strip().endswith("-hotspot"):
            return parts[0].strip()
    return None


def get_existing_profile(ssid: str) -> bool:
    if not runner.is_nmcli_available() or runner.SIMULATION_STATE["enabled"]:
        return True
    code, out = runner.run_nmcli(["-t", "-f", "NAME", "connection", "show"])
    return code == 0 and ssid in [line.strip() for line in out.splitlines()]


def connect_wifi(ssid: str, password: str = "", iface: str | None = None) -> tuple[bool, str]:
    if not ssid.strip(): return False, "SSID cannot be empty"
    suspend_watchdog(25.0)
    hotspot.stop_hotspot()
    if not runner.is_nmcli_available() or runner.SIMULATION_STATE["enabled"]:
        runner.SIMULATION_STATE["active_ssid"] = ssid
        return True, f"Connected to '{ssid}'"
    dev = iface or runner.get_wifi_interface()
    runner.run_nmcli(["connection", "delete", ssid], warn=False)
    cmd = ["device", "wifi", "connect", ssid, "ifname", dev]
    if password: cmd.extend(["password", password])
    code, out = runner.run_nmcli(cmd, timeout=30.0)
    return (True, f"Successfully connected to '{ssid}'") if code == 0 else (False, f"Connection failed: {out}")


def connect_to_wifi(ssid: str, password: str = "", iface: str | None = None) -> tuple[bool, str]:
    from src.devices.wifi.watchdog import notify_network_status
    was_hotspot = hotspot.is_hotspot_active(); ok, msg = connect_wifi(ssid, password, iface)
    if ok:
        try: save_wifi_network(ssid, password)
        except (sqlite3.Error, OSError) as e: logger.warning("Failed to save to vault: %s", e)
        hotspot.stop_emergency_hotspot(); notify_network_status(True); return True, msg
    notify_network_status(False)
    if was_hotspot: hotspot.start_emergency_hotspot()
    return False, msg

