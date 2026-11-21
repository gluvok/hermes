"""conftest.py — Global pytest fixtures for hardware and service cleanup."""
from __future__ import annotations

import os
from collections.abc import Generator

import pytest

os.environ.setdefault("SUPERADMIN_PASS", "test-admin-pass")
os.environ.setdefault("HERMES_HOTSPOT_PASS", "test-hotspot-pass")

from src.core.session import session_manager
from src.devices.scale import get_uart_reader
from src.devices.wifi.hotspot import stop_hotspot
from src.devices.wifi.portal_service import portal_service
from src.devices.wifi.watchdog import stop_wifi_watchdog


@pytest.fixture(autouse=True)
def cleanup_background_services() -> Generator[None]:
    """Ensures background threads and hardware loops are cleanly terminated after each test."""
    yield
    get_uart_reader().stop()
    stop_wifi_watchdog()
    stop_hotspot()
    portal_service.stop()
    session_manager.reset_session()
