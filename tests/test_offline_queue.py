"""test_offline_queue.py — HERMES_OFFLINE_QUEUE: drain worker, stability and LED behaviour (#42)."""
from __future__ import annotations

import sqlite3
import threading
from unittest.mock import MagicMock, patch

import pytest

from src.config import config
from src.core import db, outbox
from src.core.stability import ScaleStabilityMachine, ScaleState, scale_state_machine
from src.devices.led.colors import LEDColor
from src.devices.led.controller import RGBLedController
from src.devices.led.driver import LEDHardwareDriver


@pytest.fixture
def two_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_db_path", str(tmp_path / "q.db"))
    return outbox.enqueue(1, "MH12AB1234", 100.5, [("truck_a.jpg", b"\xff\xd8a")]), outbox.enqueue(1, "", 200.0, [])


def _drain(result):
    with patch("src.integrations.gluvok.transmit_entry_multipart", return_value=result) as send, \
         patch("src.devices.led_controller.trigger_cloud_success") as blue:
        return outbox.drain_once(), send, blue


def test_drain_success_sends_with_stored_key_removes_row_and_lights_blue(two_rows):
    handled, send, blue = _drain((True, "9", None, False))
    assert handled is True
    send.assert_called_once_with(
        center_id=1, detected_vehicle_number="MH12AB1234", weight=100.5,
        images=[("truck_a.jpg", b"\xff\xd8a")], idempotency_key=two_rows[0],
    )
    blue.assert_called_once()
    nxt = outbox.peek_oldest()
    assert nxt is not None and nxt["idempotency_key"] == two_rows[1]


def test_drain_permanent_4xx_parks_row_so_the_next_one_goes(two_rows):
    handled, _, blue = _drain((False, None, "HTTP 400: bad", False))
    assert handled is True
    blue.assert_not_called()
    nxt = outbox.peek_oldest()
    assert nxt is not None and nxt["idempotency_key"] == two_rows[1]


@pytest.mark.parametrize("err", ["HTTP 503: x", "HTTP 401: bad key", "ConnectionError: down"])
def test_drain_transient_or_auth_failure_keeps_row_at_head(two_rows, err):
    handled, _, blue = _drain((False, None, err, False))
    assert handled is False
    blue.assert_not_called()
    head = outbox.peek_oldest()
    assert head is not None and head["idempotency_key"] == two_rows[0]


def test_drain_empty_queue_does_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_db_path", str(tmp_path / "empty.db"))
    handled, send, _ = _drain((True, "1", None, False))
    assert handled is False
    send.assert_not_called()


@pytest.mark.parametrize(
    ("online", "state", "drains"),
    [
        (True, ScaleState.SCALE_IDLE, 1),
        (True, ScaleState.SCALE_STABLE_RECORDED, 1),
        (False, ScaleState.SCALE_IDLE, 0),
        (True, ScaleState.SCALE_STABILIZING, 0),
    ],
)
def test_worker_drains_only_when_online_and_not_measuring(monkeypatch, online, state, drains):
    calls: list[int] = []
    monkeypatch.setattr(scale_state_machine, "_is_online", online)
    monkeypatch.setattr(scale_state_machine, "state", state)
    monkeypatch.setattr(outbox, "drain_once", lambda: calls.append(1) or False)
    outbox._drain_pending()
    assert len(calls) == drains


class _TickEvent(threading.Event):
    """Event stand-in that lets the loop run `ticks` times, then reports stopped."""

    def __init__(self, ticks: int) -> None:
        super().__init__()
        self.ticks = ticks

    def wait(self, timeout: float | None = None) -> bool:
        self.ticks -= 1
        return self.ticks < 0


def test_worker_loop_survives_a_failing_drain(monkeypatch):
    calls: list[int] = []

    def boom() -> None:
        calls.append(1)
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(outbox, "_drain_pending", boom)
    outbox._worker_loop(_TickEvent(2), 0.0)
    assert len(calls) == 2


def test_worker_starts_once_and_stops():
    outbox.start_outbox_worker(interval=60.0)
    try:
        first = outbox._thread
        outbox.start_outbox_worker(interval=60.0)
        assert outbox.is_outbox_worker_running() and outbox._thread is first
    finally:
        outbox.stop_outbox_worker()
    assert not outbox.is_outbox_worker_running()


def _package() -> dict:
    return {"session_id": "S1", "weight": 35400.0, "anpr_plate": "HR26DK8333", "camera_snapshots": {"anpr_1": b"jpeg"}}


def test_flag_on_offline_keeps_session_and_enqueues_instead_of_posting():
    machine = ScaleStabilityMachine()
    machine.state = ScaleState.SCALE_STABILIZING
    with patch("src.core.stability.OFFLINE_QUEUE_ENABLED", True), \
         patch("src.core.stability.session_manager") as sessions, \
         patch("src.core.outbox.enqueue") as enqueue, \
         patch("src.integrations.gluvok.post_to_cloud") as post:
        machine.set_network_status(False)
        assert machine.state == ScaleState.SCALE_STABILIZING
        sessions.reset_session.assert_not_called()
        assert machine._trigger_upload(_package()) == "S1"
    enqueue.assert_called_once_with(int(config.center_id), "HR26DK8333", 35400.0, [("truck_anpr_1.jpg", b"jpeg")])
    post.assert_not_called()


def test_flag_on_enqueue_failure_is_logged_and_counted_not_swallowed(caplog):
    machine = ScaleStabilityMachine()
    with patch("src.core.stability.OFFLINE_QUEUE_ENABLED", True), \
         patch("src.core.outbox.enqueue", side_effect=sqlite3.OperationalError("disk full")), \
         patch("src.core.telemetry.record_unsent_weighment") as unsent:
        assert machine._trigger_upload(_package()) == "S1"
    unsent.assert_called_once()
    assert "disk full" in caplog.text


@pytest.mark.parametrize(("flag", "state"), [(True, ScaleState.SCALE_STABILIZING), (False, ScaleState.SCALE_IDLE)])
def test_offline_weighing_follows_the_flag(monkeypatch, flag, state):
    monkeypatch.setattr("src.core.stability.OFFLINE_QUEUE_ENABLED", flag)
    monkeypatch.setattr("src.core.stability.session_manager.check_session_progress", lambda: None)
    monkeypatch.setattr("src.core.stability.session_manager.start_session", lambda: None)
    monkeypatch.setattr("src.devices.led_controller.set_active", lambda: None)
    machine = ScaleStabilityMachine()
    machine._is_online = False
    machine.process_new_weight(config.weight_threshold + 1000.0)
    assert machine.state == state


def test_flag_on_led_stays_red_while_weighing_offline(monkeypatch):
    monkeypatch.setattr("src.devices.led.controller.OFFLINE_QUEUE_ENABLED", True)
    led = RGBLedController(driver=MagicMock(spec=LEDHardwareDriver))
    led.set_network_status(False)
    led.set_active()
    assert led.current_color == LEDColor.RED  # truck arrives while offline
    led.set_network_status(True)
    led.set_network_status(False)
    assert led.current_color == LEDColor.RED  # Wi-Fi drops mid-weighment
    led.set_idle()
    assert led.current_color == LEDColor.YELLOW
    led.cleanup()


def test_deploy_env_carries_the_flag_only_when_set(monkeypatch):
    from scripts import deploy
    monkeypatch.delenv("HERMES_OFFLINE_QUEUE", raising=False)
    assert "HERMES_OFFLINE_QUEUE" not in deploy.secrets_env_text()
    monkeypatch.setenv("HERMES_OFFLINE_QUEUE", "1")
    assert deploy.secrets_env_text().endswith('HERMES_OFFLINE_QUEUE="1"\n')
