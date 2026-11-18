import os
import tempfile
import unittest
from unittest.mock import patch

from src.core.db import init_db
from src.core.spool import drain_spool_queue, enqueue_weighment, spool_queue_count


class TestPartitionResilience(unittest.TestCase):
    def setUp(self):
        self.tmp_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.tmp_fd)
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(self.db_path + ext):
                os.remove(self.db_path + ext)

    def test_partition_accumulates_and_drains_fifo(self):
        enqueue_weighment("TRUCK_1", {"weight": 12000.0, "plate": "DL01A"})
        enqueue_weighment("TRUCK_2", {"weight": 15000.0, "plate": "DL02B"})
        self.assertEqual(spool_queue_count(), 2)

        # Disconnected: Drain skips and leaves queue intact
        with patch("src.devices.is_wifi_connected", return_value=False):
            self.assertEqual(drain_spool_queue(), 0)
            self.assertEqual(spool_queue_count(), 2)

        # Connected: Drain transmits both in FIFO order with 4-tuple return
        with patch("src.devices.is_wifi_connected", return_value=True), \
             patch("src.integrations.gluvok.post_to_cloud", return_value=(True, "ENTRY_999", None, False)):
            self.assertEqual(drain_spool_queue(), 2)
            self.assertEqual(spool_queue_count(), 0)
