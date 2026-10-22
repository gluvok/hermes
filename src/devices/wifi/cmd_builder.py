"""cmd_builder.py — Constructs CLI execution commands and termination for wifi-connect."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from src.devices.wifi.connectivity import find_wifi_connect_bin, get_wifi_interface
from src.devices.wifi.constants import UI_DIR


def build_portal_cmd(
    ssid: str, password: str, port: int, gateway: str, dhcp_range: str,
    iface: str | None, ui_dir: Path | None, timeout: int,
) -> list[str] | None:
    """Builds subprocess command line argument list for balena wifi-connect."""
    bin_path = find_wifi_connect_bin()
    if not bin_path:
        return None
    interface = iface or get_wifi_interface()
    custom_ui = str(ui_dir or UI_DIR)
    cmd = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and shutil.which("sudo") else []
    cmd.extend([
        bin_path, "--portal-ssid", ssid, "--portal-gateway", gateway,
        "--portal-dhcp-range", dhcp_range, "--portal-listening-port", str(port),
        "--portal-interface", interface, "--activity-timeout", str(timeout),
    ])
    if password:
        cmd.extend(["--portal-passphrase", password])
    if os.path.isdir(custom_ui):
        cmd.extend(["--ui-directory", custom_ui])
    return cmd


def spawn_portal_process(cmd: list[str]) -> subprocess.Popen[str] | None:
    """Spawns wifi-connect subprocess."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        time.sleep(0.5)
        return proc if proc.poll() is None else None
    except (subprocess.SubprocessError, OSError):
        return None


def terminate_process(proc: subprocess.Popen[str], timeout: float = 5.0) -> None:
    """Safely terminate or kill running process."""
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
    except (subprocess.SubprocessError, OSError):
        proc.kill()
