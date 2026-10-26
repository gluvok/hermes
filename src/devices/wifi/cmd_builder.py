"""cmd_builder.py — Constructs CLI execution commands and termination for wifi-connect."""
from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from src.devices.wifi.connectivity import find_wifi_connect_bin, get_wifi_interface
from src.devices.wifi.constants import UI_DIR

logger = logging.getLogger(__name__)


def clean_stale_portal_services() -> None:
    pfx = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and shutil.which("sudo") else []
    for t in ("dnsmasq", "wifi-connect"):
        try: subprocess.run(pfx + ["pkill", "-9", "-f", t], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0, check=False)
        except (subprocess.SubprocessError, OSError): pass


def build_portal_cmd(
    ssid: str, password: str, port: int, gateway: str, dhcp_range: str,
    iface: str | None, ui_dir: Path | None, timeout: int,
) -> list[str] | None:
    if not (bin_path := find_wifi_connect_bin()): return None
    interface, custom_ui = iface or get_wifi_interface(), str(ui_dir or UI_DIR)
    pfx = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and shutil.which("sudo") else []
    cmd = pfx + [bin_path, "--portal-ssid", ssid, "--portal-gateway", gateway, "--portal-dhcp-range", dhcp_range, "--portal-listening-port", str(port), "--portal-interface", interface, "--activity-timeout", str(timeout)]
    if password: cmd += ["--portal-passphrase", password]
    if os.path.isdir(custom_ui): cmd += ["--ui-directory", custom_ui]
    return cmd


def spawn_portal_process(cmd: list[str]) -> subprocess.Popen[str] | None:
    clean_stale_portal_services()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
        time.sleep(0.5)
        if proc.poll() is not None:
            out = proc.stdout.read().strip() if proc.stdout else ""
            msg = '[WiFi] Sudo password required! Run: echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/hermes' if "password is required" in out else f"[WiFi] wifi-connect exited immediately (code {proc.returncode}): {out}"
            logger.error(msg)
            return None
        return proc
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"[WiFi] Failed to launch wifi-connect: {e}")
        return None


def terminate_process(proc: subprocess.Popen[str], timeout: float = 3.0) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=timeout)
    except (subprocess.SubprocessError, OSError, ProcessLookupError):
        try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError): proc.kill()
    clean_stale_portal_services()
