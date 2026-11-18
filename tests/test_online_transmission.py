"""
test_online_transmission.py — Online Transmission & Offline Durability Tests
=============================================================================
Verifies that:
1. Online weighments transmit directly to Gluvok Cloud API via post_to_cloud.
2. Offline weighments are safely queued into SQLite store-and-forward table.
3. SQLite database retains Wi-Fi network credentials alongside queue tables.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from src.core.db import init_db
from src.core.spool import get_pending_weighments, spool_queue_count
from src.core.stability import ScaleStabilityMachine
from src.core.wifi_vault import get_saved_wifi_networks, save_wifi_network


class TestOnlineTransmission(unittest.TestCase):
    def setUp(self):
        self.machine = ScaleStabilityMachine()
        self.package = {
            "session_id": "SESS_TEST_ONLINE_001",
            "weight": 35400.0,
            "anpr_plate": "HR26DK8333",
            "camera_snapshots": {"anpr_1": b"fake_cam1_jpeg"},
        }

    @patch("src.integrations.gluvok.post_to_cloud")
    @patch("src.devices.is_wifi_connected", return_value=True)
    def test_online_upload_triggers_direct_cloud_post(self, mock_wifi, mock_post):
        with patch("src.devices.led_controller.trigger_cloud_success") as mock_led:
            session_id = self.machine._trigger_upload(self.package)
            self.assertEqual(session_id, "SESS_TEST_ONLINE_001")

            # Allow daemon thread a moment to execute
            time.sleep(0.1)

            mock_wifi.assert_called_once()
            mock_post.assert_called_once_with(self.package)
            mock_led.assert_called_once()

    @patch("src.integrations.gluvok.post_to_cloud")
    @patch("src.devices.is_wifi_connected", return_value=False)
    def test_offline_weighment_is_queued_to_sqlite(self, mock_wifi, mock_post):
        with tempfile.NamedTemporaryFile() as tmp:
            init_db(tmp.name)
            with patch("src.core.telemetry.record_system_event") as mock_event:
                session_id = self.machine._trigger_upload(self.package)
                self.assertEqual(session_id, "SESS_TEST_ONLINE_001")
                time.sleep(0.05)

                mock_wifi.assert_called_once()
                mock_post.assert_not_called()
                mock_event.assert_called_once_with(
                    "WEIGHMENT_QUEUED",
                    "Session SESS_TEST_ONLINE_001 queued offline: HR26DK8333 @ 35400.0kg",
                )

            # Verify weighment record exists in SQLite queue
            self.assertEqual(spool_queue_count(), 1)
            pending = get_pending_weighments()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["session_id"], "SESS_TEST_ONLINE_001")
            self.assertEqual(pending[0]["payload"]["weight"], 35400.0)

    def test_sqlite_preserves_wifi_vault_alongside_queue_table(self):
        with tempfile.NamedTemporaryFile() as tmp:
            init_db(tmp.name)

            # Wi-Fi vault should save and retrieve credentials cleanly
            save_wifi_network("Warehouse_Office", "SecretWPA2Key", db_path=tmp.name)
            saved = get_saved_wifi_networks(db_path=tmp.name)

            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["ssid"], "Warehouse_Office")

            # Confirm queue table exists and old bloated tables are absent
            with sqlite3.connect(tmp.name) as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ).fetchall()
                table_names = [t[0] for t in tables]
                self.assertIn("weighment_queue", table_names)
                self.assertNotIn("weighment_spool", table_names)
                self.assertNotIn("spool_images", table_names)

    def test_weighment_blocked_when_offline(self):
        self.machine.set_network_status(False)
        self.machine.process_new_weight(500.0)
        self.assertEqual(self.machine.state.name, "SCALE_IDLE")

    def test_network_drop_during_weighment_aborts_active_session(self):
        self.machine.set_network_status(True)
        self.machine.process_new_weight(500.0)
        self.assertEqual(self.machine.state.name, "SCALE_STABILIZING")
        self.machine.set_network_status(False)
        self.assertEqual(self.machine.state.name, "SCALE_IDLE")
