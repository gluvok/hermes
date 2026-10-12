"""Tests for SQLite database persistence."""
import sqlite3
from pathlib import Path

from src.database import DatabaseManager


def test_database_lifecycle(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    mgr = DatabaseManager(db_file)
    mgr.save_detection("test.jpg", "MH12AB1234", b"\x01\x02\x03")

    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            "SELECT filename, vehicle_number, image_blob "
            "FROM vehicle_detections"
        ).fetchone()

    assert row is not None
    assert row[0] == "test.jpg"
    assert row[1] == "MH12AB1234"
    assert row[2] == b"\x01\x02\x03"
