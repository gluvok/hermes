"""conftest.py — Global pytest fixtures for hardware and service cleanup."""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest

os.environ.setdefault("SUPERADMIN_PASS", "test-admin-pass")
os.environ.setdefault("HERMES_HOTSPOT_PASS", "test-hotspot-pass")

from src.core.outbox import stop_outbox_drain
from src.core.session import session_manager
from src.devices.scale import get_uart_reader
from src.devices.wifi.hotspot import stop_hotspot
from src.devices.wifi.portal_service import portal_service
from src.devices.wifi.watchdog import stop_wifi_watchdog


@pytest.fixture(autouse=True)
def isolated_outbox_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keeps every test's failed uploads out of the real data/hermes.db."""
    monkeypatch.setattr("src.core.outbox.get_config_db_path", lambda: str(tmp_path / "outbox.db"))


@pytest.fixture(autouse=True)
def cleanup_background_services() -> Generator[None]:
    """Ensures background threads and hardware loops are cleanly terminated after each test."""
    yield
    get_uart_reader().stop()
    stop_wifi_watchdog()
    stop_outbox_drain()
    stop_hotspot()
    portal_service.stop()
    session_manager.reset_session()
