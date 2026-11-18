"""Global pytest fixtures sandboxing hardware, serial, and subprocess execution."""

import os
import subprocess
from unittest.mock import MagicMock

import pytest

# Ensure test credentials are set in environment
os.environ.setdefault("SUPERADMIN_PASS", "Gluvok@241821")
os.environ.setdefault("DEVICE_KEY", "hardware123")

_SANDBOX_ACTIVE = True


def assert_sandbox_active():
    if not _SANDBOX_ACTIVE:
        raise RuntimeError("Sandbox inactive")


@pytest.fixture(autouse=True)
def guard_host_execution(monkeypatch):
    """Enforces simulation state and blocks raw sudo / iptables executions."""
    from src.devices.wifi.runner import SIMULATION_STATE

    SIMULATION_STATE["enabled"] = True

    orig_run = subprocess.run

    def safe_subprocess_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and any(
            arg in cmd for arg in ["sudo", "iptables", "fuser"]
        ):
            if kwargs.get("check"):
                raise RuntimeError("Direct system execution blocked in test suite")
            return subprocess.CompletedProcess(
                cmd, returncode=0, stdout=b"", stderr=b""
            )
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", safe_subprocess_run)

    # Prevent ScaleUARTReader from starting real background serial threads in web tests
    from src.devices import scale

    mock_uart = MagicMock()
    monkeypatch.setattr(scale, "get_uart_reader", lambda: mock_uart)

    # Prevent OpenCV from attempting real network RTSP connections in tests
    from src.devices import camera

    monkeypatch.setattr(camera, "_fetch_rtsp_frame", lambda url, timeout: None)
