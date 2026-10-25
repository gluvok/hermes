"""
db.py — SQLite Local Database Initialization
============================================
Thread-safe, write-ahead logged SQLite persistence layer initializing
local storage for persistent Wi-Fi credentials and runtime state.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading

from src.config.constants import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

_db_lock = threading.RLock()
_db_path: str | None = None


def get_default_db_path() -> str:
    """Computes the absolute path to the default SQLite database."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, DEFAULT_DB_PATH)


def init_db(db_path: str | None = None) -> None:
    """Initializes SQLite database with WAL mode and system tables."""
    global _db_path
    with _db_lock:
        _db_path = db_path if db_path is not None else get_default_db_path()

        dir_name = os.path.dirname(_db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with sqlite3.connect(_db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wifi_networks (
                    ssid TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

        logger.info(f"[DB] Initialized SQLite database at: {_db_path}")


def _get_connection() -> sqlite3.Connection:
    if _db_path is None:
        init_db()
    assert _db_path is not None
    conn = sqlite3.connect(_db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


__all__ = [
    "get_default_db_path",
    "init_db",
]
