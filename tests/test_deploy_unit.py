"""Generated systemd unit and sudoers drop-in for the non-root hermes service (#29)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import pytest

from scripts.deploy import (
    SUDOERS_PATH,
    build_service_unit,
    build_sudoers,
    provision_script,
)
from src.devices.wifi import portal_capport, portal_hosts, portal_redirect, runner

TARGET = "/opt/hermes"
CAPPORT_DIR = "/etc/NetworkManager/dnsmasq-shared.d"
CAPPORT_FILE = f"{CAPPORT_DIR}/hermes-captive.conf"


def _commands(text: str) -> list[str]:
    prefix = "hermes ALL=(root) NOPASSWD: "
    return [line.removeprefix(prefix) for line in text.splitlines() if line.startswith(prefix)]


def test_unit_runs_as_hermes_with_scoped_write_access() -> None:
    unit = build_service_unit(TARGET)
    assert "User=hermes\n" in unit
    assert "ProtectSystem=strict\n" in unit
    assert "AmbientCapabilities=CAP_NET_BIND_SERVICE\n" in unit
    assert f"EnvironmentFile={TARGET}/data/hermes.env\n" in unit
    rw = next(line for line in unit.splitlines() if line.startswith("ReadWritePaths=")).split("=", 1)[1].split()
    assert rw == [f"{TARGET}/data", "/etc/hosts", CAPPORT_DIR]


def test_unit_keeps_sudo_and_networkmanager_working() -> None:
    unit = build_service_unit(TARGET)
    for directive in ("NoNewPrivileges", "CapabilityBoundingSet", "PrivateDevices", "PrivateUsers", "RestrictAddressFamilies"):
        assert directive not in unit


def test_sudoers_uses_absolute_paths_and_no_wildcards() -> None:
    cmds = _commands(build_sudoers())
    assert cmds
    assert all(c.startswith("/") for c in cmds)
    assert "*" not in "".join(cmds)
    assert f"/usr/bin/tee {CAPPORT_FILE}" in cmds
    assert "/usr/bin/tee /etc/hosts" in cmds
    assert "/usr/bin/fuser -k -9 80/tcp" in cmds


def test_sudoers_rejects_unsafe_interface_name() -> None:
    with pytest.raises(ValueError):
        build_sudoers("wlan0 -j ACCEPT")


def test_provisioning_is_idempotent_and_validates_sudoers_first() -> None:
    script = provision_script(TARGET)
    assert script.index("id hermes") < script.index("useradd")
    assert script.index("visudo -cf") < script.index(f"mv {SUDOERS_PATH}.new {SUDOERS_PATH}")
    assert "install -m 0440" in script
    assert f"chown -R hermes:hermes {TARGET}/data" in script
    assert f"chmod 600 {TARGET}/data/hermes.env" in script
    assert f"mkdir -p {CAPPORT_DIR}" in script


class _Denied:
    """Path stand-in the unprivileged user cannot touch, so code falls back to sudo."""

    def __init__(self, path: str, exists: bool = True) -> None:
        self._path, self._exists = path, exists

    def __str__(self) -> str:
        return self._path

    def exists(self) -> bool:
        return self._exists

    def is_file(self) -> bool:
        return True

    def read_text(self, **_: object) -> str:
        return ""

    def mkdir(self, **_: object) -> None:
        raise PermissionError

    def write_text(self, *_: object, **__: object) -> None:
        raise PermissionError

    def write_bytes(self, *_: object, **__: object) -> None:
        raise PermissionError

    def unlink(self, **_: object) -> None:
        raise PermissionError


def test_sudoers_covers_every_sudo_argv_the_code_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[list[str]] = []

    def fake_run(cmd: list[str], *_: object, **__: object) -> subprocess.CompletedProcess[bytes]:
        ran.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    sbin = {"iptables": "/usr/sbin/iptables"}
    monkeypatch.setattr("os.geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr("shutil.which", lambda name, path=None: sbin.get(name, f"/usr/bin/{name}"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setitem(runner.SIMULATION_STATE, "enabled", False)
    monkeypatch.setattr(portal_capport, "NM_DNSMASQ_DIR", _Denied(CAPPORT_DIR))
    monkeypatch.setattr(portal_capport, "NM_CAPPORT_FILE", _Denied(CAPPORT_FILE))

    runner.run_nmcli(["connection", "up", "x"])
    portal_redirect.kill_stale_portal_listeners(80)  # the 8088 fallback never kills listeners
    for port in (80, 8088):
        portal_redirect.setup_port_forwarding("wlan0", port, portal_redirect.DEFAULT_DNS_PORT)
        portal_redirect.teardown_port_forwarding("wlan0", port, portal_redirect.DEFAULT_DNS_PORT)
    portal_capport.setup_nm_capport_config()
    portal_capport.teardown_nm_capport_config()
    portal_hosts.ensure_local_domain(hosts_path=cast("Path", _Denied("/etc/hosts")))

    allowed = set(_commands(build_sudoers("wlan0")))
    sudo_runs = [c[2:] for c in ran if c[:2] == ["sudo", "-n"]]
    assert len(sudo_runs) > 10
    for argv in sudo_runs:
        binary = argv[0] if argv[0].startswith("/") else f"/usr/bin/{argv[0]}"
        assert " ".join([binary, *argv[1:]]) in allowed or binary == "/usr/bin/nmcli", argv
    assert "/usr/bin/nmcli" in allowed
