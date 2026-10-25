"""
test_anpr_async.py — Unit Tests for Asynchronous Argus ANPR Communication
=========================================================================
Tests concurrency, non-blocking execution, session/truck association,
error isolation, and lifecycle cleanup.
"""

from __future__ import annotations

import concurrent.futures
import time
import unittest
from unittest.mock import MagicMock, patch

from src.core.session import SessionPhase, WeighbridgeSessionManager
from src.integrations.anpr import (
    dispatch_anpr_batch,
    send_and_record_anpr_frame,
)


class TestAsyncANPR(unittest.TestCase):
    def setUp(self):
        self.sm = WeighbridgeSessionManager()

    def tearDown(self):
        self.sm.reset_session()

    def test_dispatch_anpr_batch_submits_concurrently(self):
        pool = MagicMock(spec=concurrent.futures.ThreadPoolExecutor)
        mock_future = MagicMock(spec=concurrent.futures.Future)
        pool.submit.return_value = mock_future

        batch = [
            (1, b"cam1_frame_bytes"),
            (2, b"cam2_frame_bytes"),
        ]
        callback = MagicMock()

        futures = dispatch_anpr_batch(
            pool=pool,
            session_id="SESS_TEST_001",
            batch=batch,
            server_url="http://127.0.0.1:8000/recognize",
            callback=callback,
        )

        self.assertEqual(len(futures), 2)
        self.assertEqual(pool.submit.call_count, 2)

    def test_stale_session_rejection(self):
        self.sm.start_session()
        truck1_session_id = self.sm.session_id
        assert truck1_session_id is not None

        # Record valid result for current session
        accepted = self.sm.record_anpr_result(
            session_id=truck1_session_id,
            cam_idx=1,
            plate="DL01AA1111",
            status_code="SUCCESS",
        )
        self.assertTrue(accepted)
        self.assertEqual(self.sm._anpr_plates, ["DL01AA1111"])

        # Reset session (Truck 1 leaves scale)
        self.sm.reset_session()
        self.assertEqual(self.sm.phase, SessionPhase.PHASE_IDLE)

        # Start new session for Truck 2
        self.sm.start_session()
        truck2_session_id = self.sm.session_id
        self.assertNotEqual(truck1_session_id, truck2_session_id)

        # Late response from Truck 1 arrives now
        rejected = self.sm.record_anpr_result(
            session_id=truck1_session_id,
            cam_idx=2,
            plate="STALE_PLATE_TRUCK1",
            status_code="SUCCESS",
        )
        self.assertFalse(rejected)
        # Verify the late plate did not pollute Truck 2's session
        self.assertEqual(self.sm._anpr_plates, [])

    @patch("src.core.session.capture_anpr_snapshots")
    def test_anpr_loop_non_blocking_on_server_latency(self, mock_snaps):
        mock_snaps.return_value = [(1, "http://cam1/frame", b"heavy_jpeg_frame")]
        self.sm.start_session()

        # Stop background capture loop so manual dispatch can be tested in isolation
        self.sm._stop_anpr_event.set()
        if self.sm._anpr_thread:
            self.sm._anpr_thread.join(timeout=0.5)
        self.sm._anpr_plates.clear()

        # Simulate a slow network call (0.3s latency) in worker
        def slow_sender(image_bytes, **_kwargs):
            time.sleep(0.3)
            return ("MH12AB9999", "SUCCESS")

        start = time.time()
        with patch("src.core.session.send_frame_to_anpr_server", side_effect=slow_sender):
            futures = self.sm._capture_and_record_anpr_sample(wait=False)

        elapsed = time.time() - start
        # Non-blocking dispatch must return almost immediately (< 0.05s)
        self.assertLess(elapsed, 0.05)
        self.assertEqual(len(futures), 1)

        # Wait for the future to verify result eventually landed
        concurrent.futures.wait(futures, timeout=1.0)
        self.assertEqual(self.sm._anpr_plates, ["MH12AB9999"])

    def test_error_isolation_on_worker_crash(self):
        recorded_events = []

        def recording_callback(session_id, cam_idx, plate, status_code):
            recorded_events.append((session_id, cam_idx, plate, status_code))

        def crashing_sender(_img_bytes, **_kwargs):
            raise ConnectionResetError("Argus server crashed")

        plate, status = send_and_record_anpr_frame(
            session_id="SESS_ERR_TEST",
            cam_idx=1,
            image_bytes=b"crash_frame",
            callback=recording_callback,
            sender=crashing_sender,
        )

        self.assertIsNone(plate)
        self.assertEqual(status, "ANPR_WORKER_ERROR")
        self.assertEqual(len(recorded_events), 1)
        self.assertEqual(recorded_events[0], ("SESS_ERR_TEST", 1, None, "ANPR_WORKER_ERROR"))

    @patch("src.core.session.capture_anpr_snapshots")
    def test_finalize_package_drains_pending_futures(self, mock_snaps):
        mock_snaps.return_value = [(1, "http://cam1/frame", b"delayed_jpeg")]
        self.sm.start_session()

        def slightly_delayed_sender(_img_bytes, **_kwargs):
            time.sleep(0.05)
            return ("KA01MM4444", "SUCCESS")

        with patch("src.core.session.send_frame_to_anpr_server", side_effect=slightly_delayed_sender):
            self.sm._capture_and_record_anpr_sample(wait=False)

            # Trigger stabilization and fast-forward timer
            self.sm.on_weight_stabilized(34000.0)
            self.sm._post_stability_start_time = 0.0

            pkg = self.sm.check_session_progress()
            self.assertIsNotNone(pkg)
            assert pkg is not None
            # The delayed future was drained before voting
            self.assertEqual(pkg["anpr_plate"], "KA01MM4444")
