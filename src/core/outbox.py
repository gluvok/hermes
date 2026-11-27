"""
outbox.py — Persistent Outbox for Weighments the Cloud Has Not Accepted
=======================================================================
A weighment whose upload failed for a reason the server may accept later (network error,
timeout, 5xx, 429, 401/403) is stored in SQLite with its Idempotency-Key. A drain thread
replays the oldest rows every OUTBOX_DRAIN_INTERVAL_S and deletes a row on 200/201. janus
dedupes on (center, Idempotency-Key), so a replay of a row it already stored is harmless.
A 400 that survives the plate/storage fallbacks can never succeed: it is logged and dropped.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass

from src.config.constants import (
    CLOUD_MAX_IMAGES,
    OUTBOX_DRAIN_INTERVAL_S,
    OUTBOX_MAX_ROWS,
)
from src.config.store import get_config_db_path
from src.core.telemetry import (
    record_error_event,
    record_system_event,
    record_unsent_weighment,
    set_outbox_pending,
)

logger = logging.getLogger(__name__)

_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS upload_outbox (
    idempotency_key TEXT PRIMARY KEY,
    plate TEXT NOT NULL,
    weight REAL NOT NULL,
    created_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS upload_outbox_images (
    idempotency_key TEXT NOT NULL REFERENCES upload_outbox(idempotency_key) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    filename TEXT NOT NULL,
    jpeg BLOB NOT NULL,
    PRIMARY KEY (idempotency_key, position)
);
"""

# Guards SQLite writes only. Never held across network I/O (drain releases it before each POST).
_db_lock = threading.Lock()
# Guards the drain thread handle; the thread itself only reads its own stop Event.
# RLock: main.shutdown() calls stop_outbox_drain() from a signal handler on the thread that may hold it.
_state_lock = threading.RLock()
_drain_thread: threading.Thread | None = None
_drain_stop = threading.Event()


@dataclass(frozen=True)
class OutboxRow:
    key: str
    plate: str
    weight: float
    attempts: int
    images: list[tuple[str, bytes]]


@contextmanager
def _tx() -> Generator[sqlite3.Connection]:
    """One serialized transaction on a short-lived connection (commit on success, rollback on error)."""
    with _db_lock, closing(sqlite3.connect(get_config_db_path(), timeout=5.0)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_OUTBOX_DDL)
        with conn:
            yield conn


def _publish_pending(conn: sqlite3.Connection) -> int:
    pending = conn.execute("SELECT COUNT(*) FROM upload_outbox").fetchone()[0]
    set_outbox_pending(pending)
    return pending


def enqueue(key: str, plate: str, weight: float, images: list[tuple[str, bytes]]) -> bool:
    """Persists one weighment for retry. Returns False, loudly, when it could not be kept."""
    try:
        with _tx() as conn:
            full = _publish_pending(conn) >= OUTBOX_MAX_ROWS
            if not full:
                conn.execute(
                    "INSERT OR IGNORE INTO upload_outbox (idempotency_key, plate, weight, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (key, plate, weight, time.time()),
                )
                conn.executemany(
                    "INSERT OR IGNORE INTO upload_outbox_images (idempotency_key, position, filename, jpeg) "
                    "VALUES (?, ?, ?, ?)",
                    # the cloud takes at most CLOUD_MAX_IMAGES; keep only what a replay can send
                    [(key, pos, name, data) for pos, (name, data) in enumerate(images[:CLOUD_MAX_IMAGES])],
                )
                _publish_pending(conn)
    except sqlite3.Error:
        logger.exception(f"[Outbox] Could not persist weighment {key}; it is lost.")
        record_unsent_weighment()
        return False
    if full:
        message = f"Outbox full ({OUTBOX_MAX_ROWS} rows): weighment {key} ({plate}, {weight:.3f} kg) is lost."
        logger.critical(f"[Outbox] {message}")
        record_error_event("OUTBOX_FULL", message)
        record_system_event("OUTBOX_FULL", message)
        record_unsent_weighment()
        return False
    logger.warning(f"[Outbox] Queued weighment {key} ({plate}, {weight:.3f} kg) for retry.")
    return True


def next_row() -> OutboxRow | None:
    """Returns the oldest queued weighment with its images, or None when the outbox is empty."""
    with _tx() as conn:
        row = conn.execute(
            "SELECT idempotency_key, plate, weight, attempts FROM upload_outbox "
            "ORDER BY created_at, rowid LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        images = conn.execute(
            "SELECT filename, jpeg FROM upload_outbox_images WHERE idempotency_key = ? ORDER BY position",
            (row[0],),
        ).fetchall()
    return OutboxRow(row[0], row[1], row[2], row[3], [(name, bytes(data)) for name, data in images])


def remove(key: str) -> None:
    with _tx() as conn:
        conn.execute("DELETE FROM upload_outbox WHERE idempotency_key = ?", (key,))  # images cascade
        _publish_pending(conn)


def note_attempt(key: str) -> None:
    with _tx() as conn:
        conn.execute("UPDATE upload_outbox SET attempts = attempts + 1 WHERE idempotency_key = ?", (key,))


def drain_once(stop: threading.Event | None = None) -> None:
    """Replays the oldest rows until the outbox is empty or the cloud pushes back."""
    from src.integrations.gluvok import (
        is_validation_rejection,
        transmit_entry_multipart,
    )

    while (stop is None or not stop.is_set()) and (row := next_row()) is not None:
        ok, entry_id, err, _timed_out = transmit_entry_multipart(
            row.plate, row.weight, images=row.images, idempotency_key=row.key
        )
        if ok:
            remove(row.key)
            logger.info(f"[Outbox] Delivered weighment {row.key} (entry {entry_id}) after {row.attempts} retries.")
        elif is_validation_rejection(err):
            logger.error(f"[Outbox] Weighment {row.key} rejected by the cloud, dropping it: {err}")
            record_unsent_weighment()
            remove(row.key)
        else:
            # ponytail: head-of-line retry; a poisoned non-400 row blocks the queue until OUTBOX_MAX_ROWS shouts.
            note_attempt(row.key)
            logger.warning(f"[Outbox] Weighment {row.key} not delivered (attempt {row.attempts + 1}): {err}")
            return


def _drain_loop(stop: threading.Event) -> None:
    while True:
        try:
            with _tx() as conn:
                _publish_pending(conn)  # surface rows left by a previous run before the first pass
            drain_once(stop)
        except Exception:
            logger.exception("[Outbox] drain pass failed; continuing")
        if stop.wait(OUTBOX_DRAIN_INTERVAL_S):
            return


def start_outbox_drain() -> None:
    global _drain_thread, _drain_stop
    with _state_lock:
        if _drain_thread and _drain_thread.is_alive():
            return
        _drain_stop = threading.Event()  # fresh per start: a lingering old loop keeps its own, set, Event
        _drain_thread = threading.Thread(target=_drain_loop, args=(_drain_stop,), name="OutboxDrain", daemon=True)
        _drain_thread.start()


def stop_outbox_drain() -> None:
    global _drain_thread
    with _state_lock:
        thread, _drain_thread = _drain_thread, None
        _drain_stop.set()
    if thread:
        thread.join(timeout=2.0)


def is_outbox_drain_running() -> bool:
    with _state_lock:
        return bool(_drain_thread and _drain_thread.is_alive())


__all__ = [
    "OutboxRow",
    "drain_once",
    "enqueue",
    "is_outbox_drain_running",
    "next_row",
    "note_attempt",
    "remove",
    "start_outbox_drain",
    "stop_outbox_drain",
]
