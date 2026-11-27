"""outbox.py — Durable FIFO of weighments awaiting cloud upload (#42)."""
from __future__ import annotations

import base64
import json
import sqlite3
import uuid
from contextlib import closing
from typing import Any

from src.core import db

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
