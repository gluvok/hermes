"""spool.py — SQLite FIFO Store-and-Forward Weighment Queue."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from typing import Any

from src.core.db import _db_lock, _get_connection

logger = logging.getLogger(__name__)

_worker_thread: threading.Thread | None = None
_worker_stop_event = threading.Event()
_worker_lock = threading.Lock()


def enqueue_weighment(session_id: str, payload: dict[str, Any]) -> bool:
    """Commits weighment package to SQLite queue in WAL mode."""
    with _db_lock:
        conn = _get_connection()
        try:
            payload_str = json.dumps(payload, default=str)
            conn.execute(
                """
                INSERT OR REPLACE INTO weighment_queue 
                (session_id, payload_json, status, retry_count, last_error, updated_at)
                VALUES (?, ?, 'PENDING', 0, NULL, CURRENT_TIMESTAMP);
                """,
                (session_id, payload_str),
            )
            conn.commit()
            logger.info(
                f"[Spool] Enqueued offline weighment {session_id} to SQLite queue."
            )
            return True
        except (sqlite3.Error, OSError) as e:
            logger.error(f"[Spool] Failed to enqueue weighment {session_id}: {e}")
            return False


def get_pending_weighments(limit: int = 20) -> list[dict[str, Any]]:
    """Returns batch of pending weighment records sorted by creation timestamp."""
    with _db_lock:
        conn = _get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT session_id, payload_json, retry_count, last_error, created_at
                FROM weighment_queue
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                try:
                    payload = json.loads(row[1])
                except (json.JSONDecodeError, TypeError):
                    payload = {}
                results.append(
                    {
                        "session_id": row[0],
                        "payload": payload,
                        "retry_count": row[2],
                        "last_error": row[3],
                        "created_at": row[4],
                    }
                )
            return results
        except (sqlite3.Error, OSError) as e:
            logger.error(f"[Spool] Failed fetching pending weighments: {e}")
            return []


def mark_weighment_completed(session_id: str) -> bool:
    """Removes or marks a successfully transmitted weighment row as COMPLETED."""
    with _db_lock:
        conn = _get_connection()
        try:
            conn.execute(
                "DELETE FROM weighment_queue WHERE session_id = ?;",
                (session_id,),
            )
            conn.commit()
            logger.info(f"[Spool] Dequeued completed weighment {session_id}.")
            return True
        except (sqlite3.Error, OSError) as e:
            logger.error(
                f"[Spool] Failed to mark weighment completed {session_id}: {e}"
            )
            return False


def mark_weighment_failed(session_id: str, error: str) -> bool:
    """Increments retry counter and records error reason on ambiguous or network failures."""
    with _db_lock:
        conn = _get_connection()
        try:
            conn.execute(
                """
                UPDATE weighment_queue 
                SET retry_count = retry_count + 1,
                    last_error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?;
                """,
                (error, session_id),
            )
            conn.commit()
            return True
        except (sqlite3.Error, OSError) as e:
            logger.error(f"[Spool] Failed updating retry status for {session_id}: {e}")
            return False


def spool_queue_count() -> int:
    """Returns number of pending un-uploaded weighments in queue."""
    with _db_lock:
        conn = _get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM weighment_queue WHERE status = 'PENDING';"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        except (sqlite3.Error, OSError):
            return 0


def drain_spool_queue() -> int:
    """Attempts to transmit pending weighments to Gluvok API."""
    from src.devices import is_wifi_connected
    from src.integrations.gluvok import post_to_cloud

    if not is_wifi_connected():
        return 0

    pending = get_pending_weighments(limit=10)
    if not pending:
        return 0

    logger.info(f"[Spool] Draining queue: {len(pending)} pending weighments found...")
    transmitted = 0

    for item in pending:
        sid = item["session_id"]
        pkg = item["payload"]
        try:
            success, _entry_id, err, dup = post_to_cloud(pkg)
            if success or dup:
                mark_weighment_completed(sid)
                transmitted += 1
            else:
                mark_weighment_failed(sid, f"Cloud upload returned error={err}")
        except Exception as e:  # noqa: BLE001
            mark_weighment_failed(sid, str(e))

    return transmitted


def _spool_worker_loop(interval: float) -> None:
    while not _worker_stop_event.is_set():
        try:
            drain_spool_queue()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[Spool Worker] Error in drain loop: {e}")
        _worker_stop_event.wait(timeout=interval)


def start_spool_worker(interval: float = 10.0) -> None:
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_stop_event.clear()
        _worker_thread = threading.Thread(
            target=_spool_worker_loop, args=(interval,), daemon=True, name="SpoolWorker"
        )
        _worker_thread.start()
        logger.info(
            f"[Spool Worker] Started background queue worker (interval={interval}s)."
        )


def stop_spool_worker() -> None:
    global _worker_thread
    with _worker_lock:
        if _worker_thread:
            _worker_stop_event.set()
            _worker_thread.join(timeout=1.0)
            _worker_thread = None
            logger.info("[Spool Worker] Stopped.")
