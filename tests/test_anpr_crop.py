"""
test_anpr_crop.py — Unit Tests for ANPR Vehicle-Box Cropping in WeighbridgeSessionManager
=========================================================================================
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import src.services.image_compressor as _image_compressor

_image_compressor.__dict__.setdefault(
    "crop_image_bytes", lambda image_bytes, box: image_bytes
)

from src.core.session import SessionPhase, WeighbridgeSessionManager


class TestAnprVehicleCrop(unittest.TestCase):
    def setUp(self):
        self.sm = WeighbridgeSessionManager()
        self.anpr_snaps_patcher = patch(
            "src.core.session.capture_anpr_snapshots", return_value=[]
        )
        self.fleet_snaps_patcher = patch(
            "src.core.session.capture_all_camera_snapshots",
            return_value={
                "anpr_1": b"uncropped_fleet_anpr_1",
                "aux_1": b"uncropped_fleet_aux_1",
                "aux_2": b"uncropped_fleet_aux_2",
            },
        )
        self.anpr_snaps_patcher.start()
        self.fleet_snaps_patcher.start()

    def tearDown(self):
        self.anpr_snaps_patcher.stop()
        self.fleet_snaps_patcher.stop()
        self.sm.reset_session()

    def test_plate_matching_selects_latest_matching_candidate_and_crops(self):
        self.sm.start_session()
        sid = self.sm.session_id
        assert sid is not None

        self.sm.record_anpr_result(sid, 1, "MH12AB1234", "SUCCESS")
        self.sm.record_anpr_result(sid, 1, "MH12AB1234", "SUCCESS")
        self.sm.record_anpr_result(sid, 1, "OTHER9999", "SUCCESS")

        # Older matching frame, then newer matching frame, then non-matching frame
        self.sm.record_anpr_detection(
            sid, 1, "MH12AB1234", "SUCCESS", (10, 10, 100, 100), b"frame_old_match"
        )
        self.sm.record_anpr_detection(
            sid, 1, "mh12ab1234", "SUCCESS", (20, 20, 200, 200), b"frame_latest_match"
        )
        self.sm.record_anpr_detection(
            sid, 1, "OTHER9999", "SUCCESS", (30, 30, 300, 300), b"frame_other_plate"
        )

        self.sm.on_weight_stabilized(35000.0)
        self.sm._post_stability_start_time = 0.0

        with (
            patch(
                "src.core.session.crop_image_bytes",
                side_effect=lambda data, box: b"cropped:" + data + f":{box}".encode(),
            ) as mock_crop,
            patch(
                "src.core.session.compress_image_bytes",
                side_effect=lambda data: b"compressed:" + data if data else None,
            ),
        ):
            pkg = self.sm.check_session_progress()

        self.assertIsNotNone(pkg)
        assert pkg is not None
        self.assertEqual(pkg["anpr_plate"], "MH12AB1234")
        mock_crop.assert_called_once_with(b"frame_latest_match", (20, 20, 200, 200))
        self.assertEqual(
            pkg["camera_snapshots"]["anpr_1"],
            b"compressed:cropped:frame_latest_match:(20, 20, 200, 200)",
        )
        # aux cameras remain uncropped
        self.assertEqual(pkg["camera_snapshots"]["aux_1"], b"uncropped_fleet_aux_1")
        self.assertEqual(pkg["camera_snapshots"]["aux_2"], b"uncropped_fleet_aux_2")

    def test_falls_back_to_latest_valid_box_when_no_plate_match(self):
        self.sm.start_session()
        sid = self.sm.session_id
        assert sid is not None

        # No plate recognized, or different plate on this camera
        self.sm.record_anpr_detection(
            sid, 1, None, "NO_PLATE_DETECTED", (5, 5, 50, 50), b"frame_1"
        )
        self.sm.record_anpr_detection(
            sid, 1, None, "NO_PLATE_DETECTED", (15, 15, 150, 150), b"frame_2"
        )

        self.sm.on_weight_stabilized(28000.0)
        self.sm._post_stability_start_time = 0.0

        with (
            patch(
                "src.core.session.crop_image_bytes",
                side_effect=lambda data, box: b"cropped:" + data,
            ) as mock_crop,
            patch(
                "src.core.session.compress_image_bytes",
                side_effect=lambda data: data,
            ),
        ):
            pkg = self.sm.check_session_progress()

        self.assertIsNotNone(pkg)
        assert pkg is not None
        self.assertEqual(pkg["anpr_plate"], "NO_PLATE_DETECTED")
        mock_crop.assert_called_once_with(b"frame_2", (15, 15, 150, 150))
        self.assertEqual(pkg["camera_snapshots"]["anpr_1"], b"cropped:frame_2")

    def test_falls_back_to_uncropped_fleet_snapshot_when_box_missing_or_invalid(self):
        self.sm.start_session()
        sid = self.sm.session_id
        assert sid is not None

        # None box and degenerate zero-area box should be ignored
        self.assertTrue(
            self.sm.record_anpr_detection(
                sid, 1, "DL01AA1111", "SUCCESS", None, b"frame_no_box"
            )
        )
        self.assertTrue(
            self.sm.record_anpr_detection(
                sid, 1, "DL01AA1111", "SUCCESS", (10, 10, 10, 20), b"frame_zero_w"
            )
        )
        self.assertEqual(self.sm._anpr_box_candidates, {})

        self.sm.on_weight_stabilized(31000.0)
        self.sm._post_stability_start_time = 0.0

        with patch("src.core.session.crop_image_bytes") as mock_crop:
            pkg = self.sm.check_session_progress()

        self.assertIsNotNone(pkg)
        assert pkg is not None
        mock_crop.assert_not_called()
        self.assertEqual(pkg["camera_snapshots"]["anpr_1"], b"uncropped_fleet_anpr_1")
        self.assertEqual(pkg["camera_snapshots"]["aux_1"], b"uncropped_fleet_aux_1")

    def test_stale_session_rejection_and_bounded_candidates(self):
        # Idle phase rejects detection
        self.assertFalse(
            self.sm.record_anpr_detection(
                "SESS_IDLE", 1, "KA01AA0001", "SUCCESS", (0, 0, 10, 10), b"frame"
            )
        )

        self.sm.start_session()
        sid1 = self.sm.session_id
        assert sid1 is not None

        # Mismatched session rejected
        self.assertFalse(
            self.sm.record_anpr_detection(
                "SESS_OTHER", 1, "KA01AA0001", "SUCCESS", (0, 0, 10, 10), b"frame"
            )
        )
        self.assertEqual(self.sm._anpr_box_candidates, {})

        # Bounded to 5 candidates per camera
        for i in range(8):
            self.assertTrue(
                self.sm.record_anpr_detection(
                    sid1,
                    1,
                    f"PLATE_{i}",
                    "SUCCESS",
                    (i, i, i + 10, i + 10),
                    f"frame_{i}".encode(),
                )
            )
        self.assertEqual(len(self.sm._anpr_box_candidates[1]), 5)
        self.assertEqual(self.sm._anpr_box_candidates[1][0][0], "PLATE_3")
        self.assertEqual(self.sm._anpr_box_candidates[1][-1][0], "PLATE_7")

        # Reset clears candidates
        self.sm.reset_session()
        self.assertEqual(self.sm.phase, SessionPhase.PHASE_IDLE)
        self.assertEqual(self.sm._anpr_box_candidates, {})

    def test_dispatch_receives_box_callback(self):
        self.sm.start_session()
        self.sm._stop_anpr_event.set()
        if self.sm._anpr_thread and self.sm._anpr_thread.is_alive():
            self.sm._anpr_thread.join(timeout=0.5)

        mock_future = MagicMock()
        with (
            patch(
                "src.core.session.capture_anpr_snapshots",
                return_value=[(1, "http://cam1", b"img1")],
            ),
            patch(
                "src.core.session.dispatch_anpr_batch",
                return_value=[mock_future],
            ) as mock_dispatch,
        ):
            self.sm._capture_and_record_anpr_sample(wait=False)

        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        self.assertEqual(kwargs.get("box_callback"), self.sm.record_anpr_detection)
