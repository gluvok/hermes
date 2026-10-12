"""Thread-safe SQLite database manager for vehicle detections."""
import sqlite3
from pathlib import Path
from threading import Lock


class DatabaseManager:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    vehicle_number TEXT,
                    image_blob BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def save_detection(
        self, filename: str, vehicle_number: str | None, image_blob: bytes
    ) -> None:
        query = (
            "INSERT INTO vehicle_detections "
            "(filename, vehicle_number, image_blob) VALUES (?, ?, ?)"
        )
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(query, (filename, vehicle_number, image_blob))
            conn.commit()
