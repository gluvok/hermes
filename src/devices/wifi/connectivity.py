"""connectivity.py — Probes Gluvok cloud host first, with DNS socket fallback."""
from __future__ import annotations

import socket
from urllib.parse import urlparse

from src.config import constants

CHECK_TARGETS = (("1.1.1.1", 53), ("8.8.8.8", 53))


def _check_targets() -> tuple[tuple[str, int], ...]:
    parsed = urlparse(constants.GLUVOK_BASE_URL)
    if parsed.hostname:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return ((parsed.hostname, port), *CHECK_TARGETS)
    return CHECK_TARGETS


def is_network_connected(timeout: float = 1.5) -> bool:
    """Probes Gluvok cloud host first, then DNS targets, to verify connectivity."""
    # ponytail: getaddrinfo is unbounded; watchdog-thread only, so it delays detection, never UART.
    for host, port in _check_targets():
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (OSError, TimeoutError):
            continue
    return False


def is_wifi_connected(timeout: float = 1.5) -> bool:
    """Hermes compatibility alias for checking internet connectivity."""
    return is_network_connected(timeout)


__all__ = ["is_network_connected", "is_wifi_connected"]
