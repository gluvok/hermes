"""client.py — REST client submitting credentials to wifi-connect daemon."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from src.devices.wifi.connectivity import _SIMULATION_STATE, is_balena_available
from src.devices.wifi.process import balena_manager


def submit_credentials(ssid: str, password: str, timeout: float) -> tuple[bool, str]:
    """Posts Wi-Fi credentials to balena-io/wifi-connect HTTP API."""
    if not is_balena_available():
        _SIMULATION_STATE["is_connected"] = True
        _SIMULATION_STATE["current_ssid"] = ssid
        _SIMULATION_STATE["portal_running"] = False
        return True, f"Connected to '{ssid}' (simulated)."

    url = f"http://127.0.0.1:{balena_manager.portal_port}/connect"
    payload = json.dumps({"ssid": ssid, "identity": "", "passphrase": password}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode() in (200, 201, 202), f"Submitted credentials for '{ssid}'."
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return True, f"Connection initiated for '{ssid}': {e}"
