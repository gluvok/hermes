"""crop.py — Vehicle Bounding Box Cropping with Percentage Padding."""

from __future__ import annotations

import logging
from typing import Sequence

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def crop_vehicle_frame(
    image_bytes: bytes,
    box: Sequence[int | float] | None,
    pad_top_pct: float = 0.10,
    pad_bottom_pct: float = 0.10,
    pad_left_pct: float = 0.15,
    pad_right_pct: float = 0.15,
) -> bytes:
    """
    Crops image to vehicle bounding box with percentage-based padding.

    :param image_bytes: Raw JPEG bytes of full camera frame.
    :param box: (x1, y1, x2, y2) bounding box coordinates.
    :param pad_top_pct: Fraction of box height to pad above (e.g. 0.10 = 10%).
    :param pad_bottom_pct: Fraction of box height to pad below.
    :param pad_left_pct: Fraction of box width to pad on the left.
    :param pad_right_pct: Fraction of box width to pad on the right.
    :return: Cropped JPEG bytes, or original image_bytes if box is None/invalid.
    """
    if not image_bytes or not box or len(box) < 4:
        return image_bytes

    try:
        x1, y1, x2, y2 = (int(v) for v in box[:4])
        if x2 <= x1 or y2 <= y1:
            logger.debug("[Crop] Invalid bounding box coordinates: %s", box)
            return image_bytes

        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return image_bytes

        img_h, img_w = frame.shape[:2]
        bw = x2 - x1
        bh = y2 - y1

        pad_l = int(bw * max(0.0, pad_left_pct))
        pad_r = int(bw * max(0.0, pad_right_pct))
        pad_t = int(bh * max(0.0, pad_top_pct))
        pad_b = int(bh * max(0.0, pad_bottom_pct))

        crop_x1 = max(0, x1 - pad_l)
        crop_y1 = max(0, y1 - pad_t)
        crop_x2 = min(img_w, x2 + pad_r)
        crop_y2 = min(img_h, y2 + pad_b)

        if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
            return image_bytes

        cropped = frame[crop_y1:crop_y2, crop_x1:crop_x2]
        success, encoded = cv2.imencode(
            ".jpg", cropped, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        if success:
            return encoded.tobytes()
        return image_bytes
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Crop] Exception while cropping vehicle frame: %s", exc)
        return image_bytes
