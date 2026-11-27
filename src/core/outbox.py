"""outbox.py — Durable FIFO of weighments awaiting cloud upload (#42)."""
from __future__ import annotations

import base64
import json
import logging
import sqlite3
import threading
import uuid
from contextlib import closing
from typing import Any

from src.config.constants import LED_CLOUD_SUCCESS_DURATION, OUTBOX_POLL_INTERVAL
from src.core import db
from src.core.telemetry import record_system_event

logger = logging.getLogger(__name__)

OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT NOT NULL UNIQUE,
    center_id INTEGER NOT NULL,
    plate TEXT NOT NULL,
    weight REAL NOT NULL,
    images TEXT NOT NULL,              -- JSON [[filename, base64], ...]
    failed INTEGER NOT NULL DEFAULT 0, -- 1 = rejected by the server with a permanent 4xx
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _run(sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with db._db_lock, closing(sqlite3.connect(db.get_db_path(), timeout=5.0)) as conn, conn:
        conn.row_factory = sqlite3.Row
        conn.execute(OUTBOX_DDL)
        return conn.execute(sql, params).fetchall()


def enqueue(center_id: int, plate: str, weight: float, images: list[tuple[str, bytes]]) -> str:
    """Stores one weighment; returns its idempotency key."""
    key = str(uuid.uuid4())
    blob = json.dumps([[name, base64.b64encode(b).decode()] for name, b in images])
    _run(
        "INSERT INTO outbox (idempotency_key, center_id, plate, weight, images) VALUES (?, ?, ?, ?, ?)",
        (key, center_id, plate, weight, blob),
    )
    return key


def peek_oldest() -> dict[str, Any] | None:
    """Oldest entry not marked failed, or None."""
    rows = _run("SELECT * FROM outbox WHERE failed = 0 ORDER BY id LIMIT 1")
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r["id"],
        "idempotency_key": r["idempotency_key"],
        "center_id": r["center_id"],
        "plate": r["plate"],
        "weight": r["weight"],
        "images": [(n, base64.b64decode(s)) for n, s in json.loads(r["images"])],
    }


def remove(row_id: int) -> None:
    _run("DELETE FROM outbox WHERE id = ?", (row_id,))


def mark_failed(row_id: int) -> None:
    _run("UPDATE outbox SET failed = 1 WHERE id = ?", (row_id,))


def _is_permanent(err: str | None) -> bool:
    """4xx the entry itself caused. 401/403 are device-key problems: keep the row so it goes once the key is fixed."""
    # ponytail: parses gluvok's own "HTTP <code>:" error prefix; return the status code if a second caller needs it.
    return bool(err) and err.startswith("HTTP 4") and not err.startswith(("HTTP 401", "HTTP 403", "HTTP 408", "HTTP 429"))


def drain_once() -> bool:
    """Sends the oldest entry. True = row handled (sent or parked), keep draining."""
    from src.devices import led_controller
    from src.integrations.gluvok import transmit_entry_multipart

    row = peek_oldest()
    if row is None:
        return False
    ok, entry_id, err, _ = transmit_entry_multipart(
        center_id=row["center_id"], detected_vehicle_number=row["plate"], weight=row["weight"],
        images=row["images"], idempotency_key=row["idempotency_key"],
    )
    if ok:
        remove(row["id"])
        led_controller.trigger_cloud_success(LED_CLOUD_SUCCESS_DURATION)
        logger.info(f"[Outbox] Sent {row['idempotency_key']} (entry {entry_id}).")
        return True
    if _is_permanent(err):
        mark_failed(row["id"])
        record_system_event("OUTBOX", f"Entry {row['idempotency_key']} rejected: {err}")
        return True
    return False


_thread: threading.Thread | None = None
_stop = threading.Event()


def _drain_pending() -> None:
    """One entry at a time while online and not mid-measurement, so blue never cuts into a truck's red."""
    from src.core.stability import ScaleState, scale_state_machine

    # ponytail: after a backlog, older entries may pulse blue while a newly recorded truck waits its turn;
    # light blue only for the truck's own key if drivers start leaving early.
    while (
        scale_state_machine.is_online
        and scale_state_machine.state != ScaleState.SCALE_STABILIZING
        and drain_once()
    ):
        pass


def _worker_loop(stop: threading.Event, interval: float) -> None:
    while not stop.wait(interval):
        try:
            _drain_pending()
        except Exception:
            logger.exception("[Outbox] drain failed; continuing")


def start_outbox_worker(interval: float = OUTBOX_POLL_INTERVAL) -> None:
    global _thread, _stop
    if is_outbox_worker_running():
        return
    _stop = threading.Event()
    _thread = threading.Thread(target=_worker_loop, args=(_stop, interval), name="OutboxWorker", daemon=True)
    _thread.start()


def stop_outbox_worker() -> None:
    global _thread
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=2.0)
    _thread = None


def is_outbox_worker_running() -> bool:
    return bool(_thread and _thread.is_alive())
