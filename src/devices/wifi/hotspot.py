"""hotspot.py — High-level hotspot and captive portal controller."""
from __future__ import annotations

import logging
from pathlib import Path

from src.devices.led import led_controller
from src.devices.wifi.connectivity import is_wifi_connected
from src.devices.wifi.constants import (
    DEFAULT_ACTIVITY_TIMEOUT,
    DEFAULT_HOTSPOT_PASS,
    DEFAULT_HOTSPOT_SSID,
    DEFAULT_PORTAL_DHCP_RANGE,
    DEFAULT_PORTAL_GATEWAY,
    DEFAULT_PORTAL_PORT,
    UI_DIR,
)
from src.devices.wifi.process import balena_manager

logger = logging.getLogger(__name__)


def start_emergency_hotspot(
    ssid: str = DEFAULT_HOTSPOT_SSID, password: str = DEFAULT_HOTSPOT_PASS,
    portal_port: int = DEFAULT_PORTAL_PORT, gateway: str = DEFAULT_PORTAL_GATEWAY,
    dhcp_range: str = DEFAULT_PORTAL_DHCP_RANGE, interface: str | None = None,
    ui_dir: Path | None = UI_DIR, activity_timeout: int = DEFAULT_ACTIVITY_TIMEOUT,
) -> bool:
    """Start balena wifi-connect captive portal access point."""
    logger.info(f"[WiFi] Initiating balena hotspot AP: SSID='{ssid}'")
    ok = balena_manager.start_portal(
        ssid=ssid, password=password, portal_port=portal_port,
        gateway=gateway, dhcp_range=dhcp_range, interface=interface,
        ui_dir=ui_dir, activity_timeout=activity_timeout,
    )
    if not ok:
        logger.error(f"[WiFi] Failed to initiate balena hotspot AP: SSID='{ssid}'")
    led_controller.set_network_status(False)
    return ok


def stop_emergency_hotspot(timeout: float = 5.0) -> bool:
    """Stop the running balena wifi-connect captive portal."""
    logger.info("[WiFi] Stopping balena hotspot AP...")
    ok = balena_manager.stop_portal(timeout=timeout)
    led_controller.set_network_status(is_wifi_connected())
    return ok


def is_hotspot_active() -> bool:
    """Check if balena wifi-connect AP is currently active."""
    return balena_manager.is_running()


def has_hotspot_connected() -> bool:
    """Check if balena wifi-connect exited cleanly with code 0."""
    return balena_manager.has_connected()
