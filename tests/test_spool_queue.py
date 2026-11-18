"""Verify weighment sessions are spooled to SQLite during network outages and never discarded."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from src.core.db import init_db
from src.core.spool import (
    drain_spool_queue,
    enqueue_weighment,
    get_pending_weighments,
    mark_weighment_completed,
    mark_weighment_failed,
    spool_queue_count,
)


class TestSpoolQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_hermes.db")
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_weighment_enqueued_and_drained(self):
        payload = {"session_id": "TRUCK_001", "weight": 24500.0, "plate": "DL01AB1234"}
        self.assertTrue(enqueue_weighment("TRUCK_001", payload))
        self.assertEqual(spool_queue_count(), 1)

        pending = get_pending_weighments()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["session_id"], "TRUCK_001")
        self.assertEqual(pending[0]["payload"]["weight"], 24500.0)

        mark_weighment_completed("TRUCK_001")
        self.assertEqual(spool_queue_count(), 0)
        self.assertEqual(len(get_pending_weighments()), 0)

    def test_retry_count_increments_on_failure(self):
        payload = {"session_id": "TRUCK_002", "weight": 18200.0}
        self.assertTrue(enqueue_weighment("TRUCK_002", payload))

        mark_weighment_failed("TRUCK_002", "Timeout connecting to cloud")
        pending = get_pending_weighments()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["retry_count"], 1)
        self.assertEqual(pending[0]["last_error"], "Timeout connecting to cloud")

    @patch(
        "src.integrations.gluvok.post_to_cloud", return_value=(True, "CLOUD_ENTRY_999")
    )
    @patch("src.devices.is_wifi_connected", return_value=True)
    def test_drain_spool_queue_success(self, mock_wifi, mock_post):
        payload = {"session_id": "TRUCK_003", "weight": 12000.0}
        enqueue_weighment("TRUCK_003", payload)
        self.assertEqual(spool_queue_count(), 1)

        drained = drain_spool_queue()
        self.assertEqual(drained, 1)
        self.assertEqual(spool_queue_count(), 0)
        mock_post.assert_called_once_with(payload)
