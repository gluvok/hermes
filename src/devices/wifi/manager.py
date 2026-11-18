"""manager.py — Wi-Fi NetworkManager (nmcli) connection, hotspot, and watchdog manager."""
from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from typing import Any

from src.core.wifi_vault import get_saved_wifi_networks, save_wifi_network

logger = logging.getLogger(__name__)

# Operational defaults
DEFAULT_HOTSPOT_SSID = "hermes"
DEFAULT_HOTSPOT_PASS = "12345678"
HOTSPOT_CON_NAME = "hermes-hotspot"
DEFAULT_GATEWAY_IP = "10.42.0.1"
DEFAULT_HTTP_PORT = 80
DEFAULT_DNS_PORT = 5353

SIMULATION_STATE: dict[str, Any] = {
    "enabled": False,
    "hotspot_active": False,
    "active_ssid": "",
    "networks": [
        {"ssid": "Hermes_Facility_5G", "signal": 92, "security": "WPA2"},
        {"ssid": "Weighbridge_Office", "signal": 78, "security": "WPA2"},
        {"ssid": "Guest_Portal", "signal": 45, "security": "Open"},
    ],
}

_hotspot_active = False
_suspended_until = 0.0
_watchdog_thread: threading.Thread | None = None
_running = False
_watchdog_lock = threading.Lock()
_nmcli_path: str | None = None


def is_nmcli_available() -> bool:
    global _nmcli_path
    if _nmcli_path is None:
        _nmcli_path = shutil.which("nmcli") or ""
    return bool(_nmcli_path)


def run_nmcli(args: list[str], timeout: float = 15.0, warn: bool = True) -> tuple[int, str]:
    if SIMULATION_STATE["enabled"] or not is_nmcli_available():
        return 0, "simulated"
    pfx = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and shutil.which("sudo") else []
    try:
        res = subprocess.run(
            pfx + ["nmcli"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return res.returncode, (res.stdout or res.stderr).strip()
    except subprocess.TimeoutExpired:
        if warn:
            logger.warning("[WiFi] nmcli timeout after %ss: %s", timeout, " ".join(args))
        return 1, "timeout"
    except (subprocess.SubprocessError, OSError) as e:
        if warn:
            logger.warning("[WiFi] nmcli error: %s", e)
        return 1, str(e)


def get_wifi_interface() -> str:
    from pathlib import Path
    for p in Path("/sys/class/net").glob("wl*"):
        if p.is_dir():
            return p.name
    return "wlan0"


def get_hotspot_ip(iface: str | None = None) -> str:
    if SIMULATION_STATE["enabled"]:
        return DEFAULT_GATEWAY_IP
    dev = iface or get_wifi_interface()
    try:
        out = subprocess.check_output(
            ["ip", "-4", "addr", "show", dev],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except (subprocess.SubprocessError, OSError):
        pass
    return DEFAULT_GATEWAY_IP


def is_network_connected(timeout: float = 2.0) -> bool:
    for host, port in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (OSError, TimeoutError):
            continue
    return False


def is_wifi_connected(timeout: float = 2.0) -> bool:
    return is_network_connected(timeout)


def scan_networks() -> list[dict[str, Any]]:
    if SIMULATION_STATE["enabled"]:
        return list(SIMULATION_STATE["networks"])
    dev = get_wifi_interface()
    run_nmcli(["device", "wifi", "rescan", "ifname", dev], timeout=8.0, warn=False)
    code, out = run_nmcli(["-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", dev], timeout=10.0)
    if code != 0 or not out:
        return []
    nets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in out.splitlines():
        parts = line.strip().split(":")
        if not parts or not parts[0] or parts[0] in seen:
            continue
        seen.add(parts[0])
        sig = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        sec = parts[2] if len(parts) > 2 and parts[2] else "Open"
        nets.append({"ssid": parts[0], "signal": sig, "security": sec})
    return nets


def get_available_networks() -> list[dict[str, Any]]:
    return scan_networks()


def get_active_wifi_ssid() -> str:
    if SIMULATION_STATE["enabled"]:
        return str(SIMULATION_STATE.get("active_ssid", ""))
    code, out = run_nmcli(["-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
    if code != 0:
        return ""
    for line in out.splitlines():
        p = line.split(":")
        if len(p) >= 2 and p[1] in ("802-11-wireless", "wifi"):
            return p[0]
    return ""


def get_existing_profile(ssid: str) -> bool:
    if SIMULATION_STATE["enabled"]:
        return True
    code, out = run_nmcli(["-t", "-f", "NAME", "connection", "show"])
    if code != 0:
        return False
    return ssid in [l.strip() for l in out.splitlines()]


def connect_to_wifi(ssid: str, password: str = "", timeout: float = 30.0) -> tuple[bool, str]:
    if not ssid:
        return False, "SSID cannot be empty"
    suspend_watchdog(timeout + 5.0)
    target_mod = sys.modules.get("src.devices.wifi.connection", sys.modules[__name__])
    saver = getattr(target_mod, "save_wifi_network", save_wifi_network)

    if SIMULATION_STATE["enabled"]:
        SIMULATION_STATE["active_ssid"] = ssid
        saver(ssid, password)
        return True, f"Connected to {ssid} (simulated)"

    dev = get_wifi_interface()
    args = ["device", "wifi", "connect", ssid, "ifname", dev]
    if password:
        args += ["password", password]
    code, out = run_nmcli(args, timeout=timeout)
    if code == 0:
        saver(ssid, password)
        return True, f"Connected to {ssid}"
    return False, f"Connection failed: {out}"


def suspend_watchdog(seconds: float = 10.0) -> None:
    global _suspended_until
    _suspended_until = max(_suspended_until, time.time() + seconds)


def is_watchdog_suspended() -> bool:
    return time.time() < _suspended_until


def is_hotspot_active(con_name: str = HOTSPOT_CON_NAME) -> bool:
    sim = SIMULATION_STATE
    if not is_nmcli_available() or sim["enabled"]:
        return bool(sim.get("hotspot_active", _hotspot_active))
    return _hotspot_active


def start_hotspot(ssid: str = DEFAULT_HOTSPOT_SSID, password: str = DEFAULT_HOTSPOT_PASS, iface: str | None = None, con_name: str = HOTSPOT_CON_NAME) -> bool:
    global _hotspot_active
    if _hotspot_active:
        return True
    suspend_watchdog(10.0)
    if not is_nmcli_available() or SIMULATION_STATE["enabled"]:
        _hotspot_active = SIMULATION_STATE["hotspot_active"] = True
        return True

    dev = iface or get_wifi_interface()
    run_nmcli(["device", "disconnect", dev], warn=False)
    run_nmcli(["connection", "delete", con_name], warn=False)
    run_nmcli(["connection", "add", "type", "wifi", "ifname", dev, "con-name", con_name, "autoconnect", "no", "ssid", ssid])
    run_nmcli(["connection", "modify", con_name, "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg", "ipv4.method", "shared", "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password])
    code, out = run_nmcli(["connection", "up", con_name])
    if code != 0:
        run_nmcli(["connection", "delete", con_name], warn=False)
        code, out = run_nmcli(["device", "wifi", "hotspot", "ifname", dev, "con-name", con_name, "ssid", ssid, "password", password])
    _hotspot_active = (code == 0)
    suspend_watchdog(10.0)
    logger.log(logging.INFO if _hotspot_active else logging.ERROR, "[WiFi] Hotspot '%s': %s", ssid, get_hotspot_ip(dev) if _hotspot_active else out)
    return _hotspot_active


def stop_hotspot(con_name: str = HOTSPOT_CON_NAME) -> bool:
    global _hotspot_active
    suspend_watchdog(10.0)
    was_act, _hotspot_active = _hotspot_active, False
    if not is_nmcli_available() or SIMULATION_STATE["enabled"]:
        SIMULATION_STATE["hotspot_active"] = False
        return True
    if not was_act:
        return True
    code, _ = run_nmcli(["connection", "down", con_name], warn=False)
    run_nmcli(["connection", "delete", con_name], warn=False)
    return code == 0


def setup_nm_capport_config(*args: Any, **kwargs: Any) -> bool:
    from src.devices.wifi.portal import setup_nm_capport_config as _setup
    return _setup(*args, **kwargs)


def start_emergency_hotspot(ssid: str = DEFAULT_HOTSPOT_SSID, password: str = DEFAULT_HOTSPOT_PASS, iface: str | None = None) -> bool:
    target_mod = sys.modules.get("src.devices.wifi.hotspot", sys.modules[__name__])
    notifier = getattr(target_mod, "notify_network_status", notify_network_status)
    from src.devices.wifi.portal import portal_service, setup_nm_capport_config
    capporter = getattr(target_mod, "setup_nm_capport_config", setup_nm_capport_config)

    notifier(False)
    capporter()
    ok = start_hotspot(ssid, password, iface)
    dev = iface or get_wifi_interface()
    return bool(portal_service.start(ip=get_hotspot_ip(dev), iface=dev) and ok) if ok else False


def stop_emergency_hotspot(con_name: str = HOTSPOT_CON_NAME) -> bool:
    from src.devices.wifi.portal import portal_service
    portal_service.stop()
    return stop_hotspot(con_name)


def notify_network_status(online: bool) -> None:
    for mod, attr in (("src.devices.led", "led_controller"), ("src.core.stability", "scale_state_machine")):
        try:
            getattr(__import__(mod, fromlist=[attr]), attr).set_network_status(online)
        except (ImportError, AttributeError) as exc:
            logger.debug("Status update error: %s", exc)


def _watchdog_loop(interval: float = 1.0, threshold: int = 2) -> None:
    fails = 0
    target_mod = sys.modules.get("src.devices.wifi.watchdog", sys.modules[__name__])

    while _running:
        time.sleep(interval)
        if not _running or is_watchdog_suspended():
            continue
        checker = getattr(target_mod, "is_network_connected", is_network_connected)
        notifier = getattr(target_mod, "notify_network_status", notify_network_status)
        if checker():
            fails = 0
            notifier(True)
            if is_hotspot_active():
                logger.info("[Watchdog] Internet restored. Stopping emergency hotspot...")
                stop_emergency_hotspot()
        else:
            fails += 1
            if fails >= threshold or not _running:
                notifier(False)
                if not is_hotspot_active():
                    logger.warning("[Watchdog] Wi-Fi lost (%d fails). Activating hotspot...", fails)
                    start_emergency_hotspot()


def start_wifi_watchdog(interval: float = 1.0) -> bool:
    global _watchdog_thread, _running
    with _watchdog_lock:
        if _running and _watchdog_thread and _watchdog_thread.is_alive():
            return True
        _running = True
        _watchdog_thread = threading.Thread(target=_watchdog_loop, args=(interval,), daemon=True, name="WiFiWatchdog")
        _watchdog_thread.start()
        logger.info("[WiFi Watchdog] Started connectivity monitor (interval=%.1fs)", interval)
        return True


def stop_wifi_watchdog() -> None:
    global _watchdog_thread, _running
    with _watchdog_lock:
        _running = False
        if _watchdog_thread and _watchdog_thread.is_alive():
            _watchdog_thread.join(timeout=1.0)
        _watchdog_thread = None
        logger.info("[WiFi Watchdog] Stopped.")


def is_watchdog_running() -> bool:
    with _watchdog_lock:
        return bool(_running and _watchdog_thread and _watchdog_thread.is_alive())
