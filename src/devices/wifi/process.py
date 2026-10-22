"""process.py — Balena wifi-connect process lifecycle manager."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from src.devices.wifi.cmd_builder import (
    build_portal_cmd,
    spawn_portal_process,
    terminate_process,
)
from src.devices.wifi.connectivity import _SIMULATION_STATE, is_balena_available
from src.devices.wifi.constants import (
    DEFAULT_ACTIVITY_TIMEOUT,
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_PORTAL_DHCP_RANGE,
    DEFAULT_PORTAL_GATEWAY,
    DEFAULT_PORTAL_PORT,
)


class BalenaProcessManager:
    """Supervises the balena wifi-connect daemon process."""

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()
        self.portal_port: int = DEFAULT_PORTAL_PORT
        self.gateway: str = DEFAULT_PORTAL_GATEWAY

    def is_running(self) -> bool:
        with self._lock:
            if not is_balena_available():
                return bool(_SIMULATION_STATE["portal_running"])
            return self._process is not None and self._process.poll() is None

    def start_portal(
        self, ssid: str = DEFAULT_HOTSPOT_SSID, password: str = DEFAULT_HOTSPOT_PASS,
        portal_port: int = DEFAULT_PORTAL_PORT, gateway: str = DEFAULT_PORTAL_GATEWAY,
        dhcp_range: str = DEFAULT_PORTAL_DHCP_RANGE, interface: str | None = None,
        ui_dir: Path | None = None, activity_timeout: int = DEFAULT_ACTIVITY_TIMEOUT,
    ) -> bool:
        with self._lock:
            if self.is_running():
                return True
            self.portal_port, self.gateway = portal_port, gateway
            cmd = build_portal_cmd(ssid, password, portal_port, gateway, dhcp_range, interface, ui_dir, activity_timeout)
            if not cmd:
                _SIMULATION_STATE["portal_running"] = True
                return True
            self._process = spawn_portal_process(cmd)
            return self._process is not None

    def stop_portal(self, timeout: float = 5.0) -> bool:
        with self._lock:
            if not is_balena_available():
                _SIMULATION_STATE["portal_running"] = False
                return True
            if self._process and self._process.poll() is None:
                terminate_process(self._process, timeout)
            self._process = None
            return True


balena_manager = BalenaProcessManager()
