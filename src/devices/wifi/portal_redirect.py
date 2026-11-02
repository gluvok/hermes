"""portal_redirect.py — Port cleanup and iptables redirection for captive portal."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time

from src.devices.wifi.constants import DEFAULT_DNS_PORT

logger = logging.getLogger(__name__)
_PATH = os.environ.get("PATH", "") + ":/usr/sbin:/sbin:/usr/local/sbin"


def _find_bin(name: str) -> str | None:
    return shutil.which(name, path=_PATH)


def _run_cmd(cmd: list[str]) -> bool:
    pfx = ["sudo", "-n"] if getattr(os, "geteuid", lambda: 0)() != 0 and _find_bin("sudo") else []
    try:
        return subprocess.run(pfx + cmd, capture_output=True, timeout=2.0, check=False).returncode == 0
    except (subprocess.SubprocessError, OSError): return False


def kill_stale_portal_listeners(port: int = 80) -> None:
    """Terminate orphaned web servers on the captive portal port."""
    if port != 8080 and (fus := _find_bin("fuser")):
        _run_cmd([fus, "-k", "-9", f"{port}/tcp"])
    time.sleep(0.05)


def setup_port_forwarding(iface: str = "wlan0", http_port: int = 80, dns_port: int = DEFAULT_DNS_PORT) -> bool:
    """Redirect client PREROUTING and local OUTPUT traffic."""
    if not (ipt := _find_bin("iptables")): return False
    teardown_port_forwarding(iface, http_port, dns_port)
    hp, dp, ok = str(http_port), str(dns_port), True
    if http_port != 80:
        ok &= _run_cmd([ipt, "-t", "nat", "-A", "PREROUTING", "-i", iface, "-p", "tcp", "--dport", "80", "-j", "REDIRECT", "--to-ports", hp])
        _run_cmd([ipt, "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "-o", "lo", "--dport", "80", "-j", "REDIRECT", "--to-ports", hp])
        _run_cmd([ipt, "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "-d", "10.42.0.1", "--dport", "80", "-j", "REDIRECT", "--to-ports", hp])
    ok &= _run_cmd([ipt, "-t", "nat", "-A", "PREROUTING", "-i", iface, "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", dp])
    _run_cmd([ipt, "-t", "nat", "-A", "PREROUTING", "-i", iface, "-p", "tcp", "--dport", "53", "-j", "REDIRECT", "--to-ports", dp])
    if ok: logger.info("[Redirect] iptables active: HTTP=%s, DNS :53 -> :%s", hp, dp)
    return ok


def teardown_port_forwarding(iface: str = "wlan0", http_port: int = 80, dns_port: int = DEFAULT_DNS_PORT) -> None:
    """Remove active iptables PREROUTING and OUTPUT redirection rules."""
    if not (ipt := _find_bin("iptables")): return
    hp, dp = str(http_port), str(dns_port)
    _run_cmd([ipt, "-t", "nat", "-D", "PREROUTING", "-i", iface, "-p", "tcp", "--dport", "80", "-j", "REDIRECT", "--to-ports", hp])
    _run_cmd([ipt, "-t", "nat", "-D", "OUTPUT", "-p", "tcp", "-o", "lo", "--dport", "80", "-j", "REDIRECT", "--to-ports", hp])
    _run_cmd([ipt, "-t", "nat", "-D", "OUTPUT", "-p", "tcp", "-d", "10.42.0.1", "--dport", "80", "-j", "REDIRECT", "--to-ports", hp])
    _run_cmd([ipt, "-t", "nat", "-D", "PREROUTING", "-i", iface, "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", dp])
    _run_cmd([ipt, "-t", "nat", "-D", "PREROUTING", "-i", iface, "-p", "tcp", "--dport", "53", "-j", "REDIRECT", "--to-ports", dp])


__all__ = ["kill_stale_portal_listeners", "setup_port_forwarding", "teardown_port_forwarding"]
