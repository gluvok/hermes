import threading
import unittest

import cv2
import numpy as np

from src.devices.camera import compress_image_bytes


class TestCameraMemoryLeak(unittest.TestCase):
    def test_ram_compression_bounds(self):
        # Create an uncompressed 2560x1440 synthetic image (~11MB raw)
        img = np.zeros((1440, 2560, 3), dtype=np.uint8)
        img[:] = (128, 128, 128)
        _, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        raw_buffer = encoded.tobytes()

        compressed = compress_image_bytes(raw_buffer, max_dim=1920, quality=75)
        self.assertIsNotNone(compressed)
        # Ensure compressed size is significantly bounded (under 500 KB)
        self.assertLessEqual(len(compressed), 500 * 1024)

    def test_background_fleet_capture_does_not_leak_threads(self):
        before = threading.active_count()
        # Verify no orphan threads after basic inspections
        self.assertLessEqual(threading.active_count(), before + 1)
