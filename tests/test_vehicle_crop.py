from __future__ import annotations

import cv2
import numpy as np

from src.devices.crop import crop_vehicle_frame


def _create_synthetic_jpeg(width: int = 640, height: int = 480) -> bytes:
    """Create a synthetic solid colored image encoded as JPEG."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)  # Solid gray
    # Draw a green rectangle in the center
    img[100:300, 100:300] = (0, 255, 0)
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


def test_crop_vehicle_frame_with_padding():
    raw_jpeg = _create_synthetic_jpeg(640, 480)
    box = (100, 100, 300, 300)

    # 10% pad top/bottom = 20px -> height 240
    # 15% pad left/right = 30px -> width 260
    cropped_jpeg = crop_vehicle_frame(
        raw_jpeg,
        box=box,
        pad_top_pct=0.10,
        pad_bottom_pct=0.10,
        pad_left_pct=0.15,
        pad_right_pct=0.15,
    )

    assert cropped_jpeg != raw_jpeg
    nparr = np.frombuffer(cropped_jpeg, np.uint8)
    cropped_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert cropped_img is not None
    h, w = cropped_img.shape[:2]
    assert w == 260
    assert h == 240


def test_crop_boundary_clamping():
    raw_jpeg = _create_synthetic_jpeg(640, 480)
    # Box near border: 20px from edge
    box = (20, 20, 620, 460)

    # 20% pad extends beyond 0 and 640/480
    cropped_jpeg = crop_vehicle_frame(
        raw_jpeg,
        box=box,
        pad_top_pct=0.20,
        pad_bottom_pct=0.20,
        pad_left_pct=0.20,
        pad_right_pct=0.20,
    )

    nparr = np.frombuffer(cropped_jpeg, np.uint8)
    cropped_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert cropped_img is not None
    h, w = cropped_img.shape[:2]
    # Should clamp exactly to image limits (640x480)
    assert w == 640
    assert h == 480


def test_crop_fallback_on_none_or_invalid_box():
    raw_jpeg = _create_synthetic_jpeg(640, 480)

    # None box
    assert crop_vehicle_frame(raw_jpeg, box=None) == raw_jpeg

    # Inverted box (invalid)
    assert crop_vehicle_frame(raw_jpeg, box=(300, 300, 100, 100)) == raw_jpeg

    # Empty bytes
    assert crop_vehicle_frame(b"", box=(10, 10, 50, 50)) == b""
