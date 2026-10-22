"""discovery.py — Network scanning via balena wifi-connect REST API."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from src.devices.wifi.connectivity import is_balena_available
from src.devices.wifi.process import balena_manager

logger = logging.getLogger(__name__)


def fetch_scanned_networks(
    portal_host: str = "127.0.0.1", port: int | None = None
) -> list[dict[str, Any]]:
    """Query balena wifi-connect REST API for scanned Wi-Fi access points."""
    target_port = port or balena_manager.portal_port
    if not is_balena_available():
        return [
            {"ssid": "Office_WiFi_5G", "signal": -42, "security": "WPA2-PSK"},
            {"ssid": "Guest_Network", "signal": -58, "security": "Open"},
            {"ssid": "Warehouse_AP_North", "signal": -72, "security": "WPA2-PSK"},
            {"ssid": "MobileHotspot", "signal": -35, "security": "WPA2-PSK"},
        ]

    endpoints = (
        f"http://{portal_host}:{target_port}/networks",
        f"http://{portal_host}:{target_port}/ssids",
    )
    for ep in endpoints:
        try:
            req = urllib.request.Request(ep, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            logger.debug("Failed querying discovery endpoint %s: %s", ep, e)
    return []


def get_available_networks() -> list[dict[str, Any]]:
    """Return available Wi-Fi access points scanned by balena wifi-connect."""
    return fetch_scanned_networks()


def get_existing_profile(ssid: str) -> str | None:
    """Returns profile name if SSID is known in persistent storage."""
    from src.core.wifi_vault import get_wifi_password

    return ssid if get_wifi_password(ssid) is not None else None
