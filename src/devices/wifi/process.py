"""process.py — Balena wifi-connect process lifecycle manager."""
from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path

from src.devices.wifi import cmd_builder as cb
from src.devices.wifi import constants as c
from src.devices.wifi.connectivity import _SIMULATION_STATE, is_balena_available

logger = logging.getLogger(__name__)


class BalenaProcessManager:
    """Supervises the balena wifi-connect daemon process."""

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()
        self.portal_port, self.gateway = c.DEFAULT_PORTAL_PORT, c.DEFAULT_PORTAL_GATEWAY

    def is_running(self) -> bool:
        with self._lock:
            avail = is_balena_available()
            return self._process is not None and self._process.poll() is None if avail else bool(_SIMULATION_STATE["portal_running"])

    def has_connected(self) -> bool:
        with self._lock:
            avail = is_balena_available()
            return self._process is not None and self._process.poll() == 0 if avail else bool(_SIMULATION_STATE.get("has_connected", False))

    def exit_details(self) -> tuple[int | None, str]:
        with self._lock:
            if not self._process: return None, ""
            code = self._process.poll()
            return code, (self._process.stdout.read().strip() if (code and self._process.stdout) else "")

    def start_portal(
        self, ssid: str = c.DEFAULT_HOTSPOT_SSID, password: str = c.DEFAULT_HOTSPOT_PASS, portal_port: int = c.DEFAULT_PORTAL_PORT,
        gateway: str = c.DEFAULT_PORTAL_GATEWAY, dhcp_range: str = c.DEFAULT_PORTAL_DHCP_RANGE, interface: str | None = None,
        ui_dir: Path | None = None, activity_timeout: int = c.DEFAULT_ACTIVITY_TIMEOUT,
    ) -> bool:
        with self._lock:
            if self.is_running(): return True
            _SIMULATION_STATE["has_connected"] = False
            self.portal_port, self.gateway = portal_port, gateway
            if not (cmd := cb.build_portal_cmd(ssid, password, portal_port, gateway, dhcp_range, interface, ui_dir, activity_timeout)):
                logger.error("[WiFi] wifi-connect binary not found. Cannot start hotspot.")
                _SIMULATION_STATE["portal_running"] = False
                return False
            self._process = cb.spawn_portal_process(cmd)
            return self._process is not None

    def stop_portal(self, timeout: float = 5.0) -> bool:
        with self._lock:
            _SIMULATION_STATE["portal_running"] = _SIMULATION_STATE["has_connected"] = False
            if self._process: cb.terminate_process(self._process, timeout)
            else: cb.clean_stale_portal_services()
            self._process = None
            return True


balena_manager = BalenaProcessManager()
