"""
test_online_transmission.py — Online Transmission & Offline Discard Tests
==========================================================================
Verifies that:
1. Online weighments transmit directly to Gluvok Cloud API via post_to_cloud.
2. Offline weighments are safely discarded with zero database writes.
3. SQLite database retains Wi-Fi network credentials while spool tables are removed.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from unittest.mock import ANY, patch

from src.core.db import init_db
from src.core.stability import ScaleStabilityMachine, ScaleState
from src.core.telemetry import (
    get_outbox_pending,
    get_unsent_weighment_count,
    reset_telemetry,
)
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

    @patch("src.integrations.gluvok.post_to_cloud", return_value=(True, "42", None, False))
    @patch("src.devices.is_wifi_connected", return_value=True)
    def test_online_upload_triggers_direct_cloud_post(self, mock_wifi, mock_post):
        self.machine._is_online = True
        with patch("src.devices.led_controller.trigger_cloud_success") as mock_led:
            session_id = self.machine._trigger_upload(self.package)
            self.assertEqual(session_id, "SESS_TEST_ONLINE_001")

            # Allow daemon thread a moment to execute
            time.sleep(0.1)

            # Reuses the watchdog's verdict; never probes on the UART thread (#19).
            mock_wifi.assert_not_called()
            mock_post.assert_called_once_with(self.package, idempotency_key=ANY)
            mock_led.assert_called_once()

    @patch("src.integrations.gluvok.post_to_cloud")
    @patch("src.devices.is_wifi_connected", return_value=True)
    def test_offline_weighment_is_discarded_with_zero_db_writes(self, mock_wifi, mock_post):
        self.machine._is_online = False
        with tempfile.NamedTemporaryFile() as tmp:
            init_db(tmp.name)
            with patch("src.core.telemetry.record_system_event") as mock_event:
                session_id = self.machine._trigger_upload(self.package)
                self.assertEqual(session_id, "SESS_TEST_ONLINE_001")
                time.sleep(0.05)

                mock_wifi.assert_not_called()
                mock_post.assert_not_called()
                mock_event.assert_called_once_with(
                    "WEIGHMENT_DISCARDED",
                    "Session SESS_TEST_ONLINE_001 discarded: Wi-Fi offline",
                )

            # Verify no weighment records exist in SQLite
            with sqlite3.connect(tmp.name) as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ).fetchall()
                table_names = [t[0] for t in tables]
                self.assertNotIn("weighment_spool", table_names)
                self.assertNotIn("spool_images", table_names)

    def test_sqlite_preserves_wifi_vault_without_spool_tables(self):
        with tempfile.NamedTemporaryFile() as tmp:
            init_db(tmp.name)

            # Wi-Fi vault should save and retrieve credentials cleanly
            save_wifi_network("Warehouse_Office", "SecretWPA2Key", db_path=tmp.name)
            saved = get_saved_wifi_networks(db_path=tmp.name)

            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["ssid"], "Warehouse_Office")

            # Confirm spool tables are completely absent
            with sqlite3.connect(tmp.name) as conn:
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute("SELECT * FROM weighment_spool;")
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute("SELECT * FROM spool_images;")

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


@patch("src.devices.led_controller")
@patch(
    "src.integrations.gluvok.post_to_cloud",
    return_value=(False, None, "HTTP 401: no", False),
)
def test_failed_upload_does_not_light_cloud_success(mock_post, mock_led):
    ScaleStabilityMachine()._transmit_online_weighment({"session_id": "S1"})
    mock_led.trigger_cloud_success.assert_not_called()


@patch("src.devices.led_controller")
@patch("src.integrations.gluvok.post_to_cloud", return_value=(True, "42", None, False))
def test_successful_upload_lights_cloud_success(mock_post, mock_led):
    ScaleStabilityMachine()._transmit_online_weighment({"session_id": "S1"})
    mock_led.trigger_cloud_success.assert_called_once()


@patch("src.devices.led_controller")
@patch("src.core.stability.session_manager")
def test_drop_below_threshold_during_session_sets_led_idle(mock_sm, mock_led):
    m = ScaleStabilityMachine()
    m.state = ScaleState.SCALE_STABILIZING
    m._handle_zero_or_subthreshold(1.0)  # > 0, < threshold
    mock_led.set_idle.assert_called_once()


@patch("src.devices.led_controller")
@patch(
    "src.integrations.gluvok.post_to_cloud",
    return_value=(False, None, "HTTP 500: boom", False),
)
def test_failed_upload_is_queued_not_lost(mock_post, mock_led):
    reset_telemetry()
    ScaleStabilityMachine()._transmit_online_weighment({"session_id": "S1"})
    assert get_unsent_weighment_count() == 0
    assert get_outbox_pending() == 1


@patch("src.devices.led_controller")
@patch("src.integrations.gluvok.post_to_cloud", side_effect=OSError("link down"))
def test_upload_exception_is_queued_not_lost(mock_post, mock_led):
    reset_telemetry()
    ScaleStabilityMachine()._transmit_online_weighment({"session_id": "S1"})
    assert get_unsent_weighment_count() == 0
    assert get_outbox_pending() == 1


@patch("src.devices.led_controller")
@patch("src.integrations.gluvok.post_to_cloud", return_value=(True, "42", None, False))
def test_successful_upload_does_not_count_as_unsent(mock_post, mock_led):
    reset_telemetry()
    ScaleStabilityMachine()._transmit_online_weighment({"session_id": "S1"})
    assert get_unsent_weighment_count() == 0


def test_offline_discard_counts_as_unsent():
    reset_telemetry()
    machine = ScaleStabilityMachine()
    machine._is_online = False
    machine._trigger_upload({"session_id": "S1"})
    assert get_unsent_weighment_count() == 1


def test_reset_telemetry_zeroes_unsent_count():
    reset_telemetry()
    from src.core.telemetry import record_unsent_weighment

    record_unsent_weighment()
    assert get_unsent_weighment_count() == 1
    reset_telemetry()
    assert get_unsent_weighment_count() == 0
