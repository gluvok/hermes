"""test_outbox.py — A failed upload is persisted, replayed with the same key, and a 400 is dropped."""
from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest

from src.config import ConfigManager
from src.config.constants import CLOUD_AUTH_ALERT_THRESHOLD
from src.core import outbox
from src.core.stability import ScaleStabilityMachine
from src.core.telemetry import (
    get_cloud_auth_failures,
    get_error_counts,
    get_outbox_pending,
    get_unsent_weighment_count,
    reset_telemetry,
)

PACKAGE = {
    "session_id": "S1",
    "weight": 18540.5,
    "anpr_plate": "MH12AB1234",
    "camera_snapshots": {"anpr_1": b"jpeg-1", "aux_2": b"jpeg-2"},
}
OK = (201, b'{"data":{"id":7}}')


@pytest.fixture(autouse=True)
def _fresh_telemetry() -> None:
    reset_telemetry()


@pytest.fixture
def cloud(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[list[tuple[int, bytes]], list[str | None]]]:
    """Local janus stand-in. Yields (script, seen): scripted (status, body) replies, Idempotency-Keys received."""
    script: list[tuple[int, bytes]] = [OK]
    seen: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            status, body = script[min(len(seen), len(script) - 1)]
            seen.append(self.headers.get("Idempotency-Key"))
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr("src.integrations.gluvok.GLUVOK_BASE_URL", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setattr(ConfigManager, "device_key", "test-device-key")
    monkeypatch.setattr(ConfigManager, "device_id", "test-device")
    yield script, seen
    server.shutdown()
    server.server_close()


def test_failed_post_is_persisted_with_its_key():
    failure = (False, None, "HTTP 503: down", False)
    with patch("src.integrations.gluvok.post_to_cloud", return_value=failure) as post:
        ScaleStabilityMachine()._transmit_online_weighment(PACKAGE)

    key = post.call_args.kwargs["idempotency_key"]
    assert uuid.UUID(key).version == 7
    row = outbox.next_row()
    assert row is not None
    assert (row.key, row.plate, row.weight, row.attempts) == (key, "MH12AB1234", 18540.5, 0)
    assert row.images == [("truck_anpr_1.jpg", b"jpeg-1"), ("truck_aux_2.jpg", b"jpeg-2")]
    assert get_outbox_pending() == 1
    assert get_unsent_weighment_count() == 0


def test_drain_delivers_with_the_same_key_and_deletes_the_row(cloud):
    script, seen = cloud
    script[:] = [(401, b"Unauthorized"), OK]  # the cutover 401, then janus accepts the key

    ScaleStabilityMachine()._transmit_online_weighment(PACKAGE)
    assert outbox.next_row() is not None

    outbox.drain_once()

    assert len(seen) == 2 and seen[0] == seen[1]
    assert uuid.UUID(seen[0] or "").version == 7
    assert outbox.next_row() is None
    assert get_outbox_pending() == 0
    with sqlite3.connect(outbox.get_config_db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM upload_outbox_images").fetchone()[0] == 0


def test_400_after_the_fallbacks_is_dropped(cloud):
    script, seen = cloud
    script[:] = [(400, b"Invalid weight")]

    ScaleStabilityMachine()._transmit_online_weighment(PACKAGE)  # a 400 is terminal on the first attempt too
    assert outbox.next_row() is None
    assert get_unsent_weighment_count() == 1

    outbox.enqueue(str(uuid.uuid7()), "MH12AB1234", 18540.5, [])  # and when a replayed row is rejected
    outbox.drain_once()

    assert outbox.next_row() is None
    assert get_unsent_weighment_count() == 2
    assert len(seen) == 2  # one POST each, no re-post of a bad weight


def test_401_keeps_the_row_and_flags_a_sustained_auth_failure(cloud):
    script, seen = cloud
    script[:] = [(401, b"Unauthorized")]
    key = str(uuid.uuid7())
    outbox.enqueue(key, "MH12AB1234", 18540.5, [("truck_anpr_1.jpg", b"jpeg-1")])

    for _ in range(CLOUD_AUTH_ALERT_THRESHOLD):
        outbox.drain_once()

    row = outbox.next_row()
    assert row is not None and row.key == key
    assert row.attempts == CLOUD_AUTH_ALERT_THRESHOLD
    assert seen == [key] * CLOUD_AUTH_ALERT_THRESHOLD
    assert get_cloud_auth_failures() >= CLOUD_AUTH_ALERT_THRESHOLD

    script[:] = [OK]
    outbox.drain_once()
    assert outbox.next_row() is None
    assert get_cloud_auth_failures() == 0


def test_full_outbox_refuses_loudly_instead_of_dropping_silently(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(outbox, "OUTBOX_MAX_ROWS", 1)

    assert outbox.enqueue("k1", "MH12AB1234", 1.0, [])
    assert not outbox.enqueue("k2", "MH12AB1234", 2.0, [])

    row = outbox.next_row()
    assert row is not None and row.key == "k1"  # the oldest row is kept
    assert get_outbox_pending() == 1
    assert get_unsent_weighment_count() == 1
    assert get_error_counts()["OUTBOX_FULL"] == 1


def test_drain_thread_delivers_in_the_background_and_stops(cloud):
    outbox.enqueue(str(uuid.uuid7()), "MH12AB1234", 18540.5, [])

    outbox.start_outbox_drain()
    assert outbox.is_outbox_drain_running()
    deadline = time.monotonic() + 5.0
    while outbox.next_row() is not None and time.monotonic() < deadline:
        time.sleep(0.05)
    outbox.stop_outbox_drain()

    assert outbox.next_row() is None
    assert not outbox.is_outbox_drain_running()


def test_concurrent_enqueues_all_land():
    threads = [
        threading.Thread(
            target=lambda n=n: [outbox.enqueue(f"k{n}-{i}", "MH12AB1234", 1.0, []) for i in range(10)]
        )
        for n in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert get_outbox_pending() == 80
    with sqlite3.connect(outbox.get_config_db_path()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM upload_outbox").fetchone()[0] == 80
