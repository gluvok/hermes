import os
import sqlite3
import tempfile
import unittest

from src.core.db import init_db
from src.core.spool import enqueue_weighment


class TestDbCrashDurability(unittest.TestCase):
    def test_unclean_reboot_preserves_pending_queue(self):
        tmp_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(tmp_fd)

        try:
            init_db(db_path)
            # Enqueue session before crash
            enqueue_weighment(
                "CRASH_TEST_01", {"weight": 14200.0, "plate": "DL01AB1234"}
            )

            # Simulate abrupt process termination without graceful close
            # Verify WAL journal integrity upon re-opening
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

            cursor = conn.execute("SELECT session_id, status FROM weighment_queue;")
            row = cursor.fetchone()
            self.assertEqual(row[0], "CRASH_TEST_01")
            self.assertEqual(row[1], "PENDING")
            conn.close()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            for ext in ["-wal", "-shm"]:
                if os.path.exists(db_path + ext):
                    os.remove(db_path + ext)
