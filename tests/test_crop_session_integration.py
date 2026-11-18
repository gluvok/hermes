import unittest
from unittest.mock import MagicMock, patch
import cv2
import numpy as np

from src.core.session import WeighbridgeSessionManager, SessionPhase
from src.config import config


class TestCropSessionIntegration(unittest.TestCase):
    def setUp(self):
        # Create a synthetic 400x400 image (JPEG bytes)
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        img[100:300, 100:300] = [0, 255, 0]  # green center box
        _, enc = cv2.imencode(".jpg", img)
        self.sample_jpeg = enc.tobytes()

    def test_record_anpr_result_stores_vehicle_box(self):
        mgr = WeighbridgeSessionManager()
        mgr.session_id = "TEST_SESS_1"
        mgr.phase = SessionPhase.PHASE_STABILIZING

        mgr.record_anpr_result(
            "TEST_SESS_1", 1, "MH12AB1234", "SUCCESS", vehicle_box=(100, 100, 300, 300)
        )
        self.assertEqual(mgr._last_vehicle_box, (100, 100, 300, 300))

    def test_finalize_package_crops_anpr_1_with_configured_padding(self):
        mgr = WeighbridgeSessionManager()
        mgr.session_id = "TEST_SESS_2"
        mgr.phase = SessionPhase.PHASE_STABILIZING
        mgr.stable_weight = 12500.0

        # Inject frames into buffer
        mgr._anpr_frame_buffers[1] = [self.sample_jpeg]
        mgr._anpr_plates.append("KA01CD5678")
        mgr._last_vehicle_box = (100, 100, 300, 300)

        # Set padding to 0% to get exact box (200x200)
        config.runtime.update_system(
            crop_pad_top=0.0,
            crop_pad_bottom=0.0,
            crop_pad_left=0.0,
            crop_pad_right=0.0,
        )
        try:
            pkg = mgr._finalize_session_package()
        finally:
            config.runtime.update_system(
                crop_pad_top=10.0,
                crop_pad_bottom=10.0,
                crop_pad_left=15.0,
                crop_pad_right=15.0,
            )

        cropped_bytes = pkg["camera_snapshots"]["anpr_1"]
        self.assertIsNotNone(cropped_bytes)

        # Decode cropped image and assert its shape matches cropped box
        arr = np.frombuffer(cropped_bytes, dtype=np.uint8)
        dec = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = dec.shape[:2]
        self.assertEqual((w, h), (200, 200))

    def test_finalize_package_falls_back_when_no_vehicle_box(self):
        mgr = WeighbridgeSessionManager()
        mgr.session_id = "TEST_SESS_3"
        mgr.phase = SessionPhase.PHASE_STABILIZING
        mgr.stable_weight = 8000.0

        mgr._anpr_frame_buffers[1] = [self.sample_jpeg]
        mgr._last_vehicle_box = None

        pkg = mgr._finalize_session_package()
        out_bytes = pkg["camera_snapshots"]["anpr_1"]
        self.assertIsNotNone(out_bytes)

        arr = np.frombuffer(out_bytes, dtype=np.uint8)
        dec = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = dec.shape[:2]
        # Should remain full original dimensions
        self.assertEqual((w, h), (400, 400))
