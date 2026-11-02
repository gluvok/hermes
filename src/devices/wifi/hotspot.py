"""hotspot.py — Manages the emergency Wi-Fi hotspot AP via nmcli."""
from __future__ import annotations

import logging

from src.devices.wifi import constants, runner
from src.devices.wifi.activity import suspend_watchdog
from src.devices.wifi.ip import get_hotspot_ip
from src.devices.wifi.portal_capport import setup_nm_capport_config

logger = logging.getLogger(__name__)
_hotspot_active = False
C_SSID, C_PASS, C_CON = constants.DEFAULT_HOTSPOT_SSID, constants.DEFAULT_HOTSPOT_PASS, constants.HOTSPOT_CON_NAME

def is_hotspot_active(con_name: str = C_CON) -> bool:
    sim = runner.SIMULATION_STATE
    return bool(sim.get("hotspot_active", _hotspot_active)) if not runner.is_nmcli_available() or sim["enabled"] else _hotspot_active


def start_hotspot(ssid: str = C_SSID, password: str = C_PASS, iface: str | None = None, con_name: str = C_CON) -> bool:
    global _hotspot_active
    if _hotspot_active: return True
    suspend_watchdog(10.0)
    if not runner.is_nmcli_available() or runner.SIMULATION_STATE["enabled"]:
        _hotspot_active = runner.SIMULATION_STATE["hotspot_active"] = True; return True
    dev = iface or runner.get_wifi_interface()
    runner.run_nmcli(["device", "disconnect", dev], warn=False)
    runner.run_nmcli(["connection", "delete", con_name], warn=False)
    runner.run_nmcli(["connection", "add", "type", "wifi", "ifname", dev, "con-name", con_name, "autoconnect", "no", "ssid", ssid])
    runner.run_nmcli(["connection", "modify", con_name, "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg", "ipv4.method", "shared", "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password])
    code, out = runner.run_nmcli(["connection", "up", con_name])
    if code != 0:
        runner.run_nmcli(["connection", "delete", con_name], warn=False)
        code, out = runner.run_nmcli(["device", "wifi", "hotspot", "ifname", dev, "con-name", con_name, "ssid", ssid, "password", password])
    _hotspot_active = (code == 0); suspend_watchdog(10.0)
    logger.log(logging.INFO if _hotspot_active else logging.ERROR, "[WiFi] Hotspot '%s': %s", ssid, get_hotspot_ip(dev) if _hotspot_active else out)
    return _hotspot_active


def stop_hotspot(con_name: str = C_CON) -> bool:
    global _hotspot_active
    suspend_watchdog(10.0); was_act, _hotspot_active = _hotspot_active, False
    if not runner.is_nmcli_available() or runner.SIMULATION_STATE["enabled"]:
        runner.SIMULATION_STATE["hotspot_active"] = False; return True
    if not was_act: return True
    code, _ = runner.run_nmcli(["connection", "down", con_name], warn=False)
    runner.run_nmcli(["connection", "delete", con_name], warn=False); return code == 0


def start_emergency_hotspot(ssid: str = C_SSID, password: str = C_PASS, iface: str | None = None) -> bool:
    from src.devices.wifi.portal_service import portal_service
    from src.devices.wifi.watchdog import notify_network_status
    notify_network_status(False); setup_nm_capport_config(); ok = start_hotspot(ssid, password, iface)
    dev = iface or runner.get_wifi_interface()
    return bool(portal_service.start(ip=get_hotspot_ip(dev), iface=dev) and ok) if ok else False


def stop_emergency_hotspot(con_name: str = C_CON) -> bool:
    from src.devices.wifi.portal_service import portal_service
    portal_service.stop(); return stop_hotspot(con_name)
