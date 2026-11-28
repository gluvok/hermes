"""image_compressor.py — High-clarity JPEG compression for fleet camera captures."""
from __future__ import annotations

import math
from collections.abc import Sequence

import cv2
import numpy as np


def _encode_jpeg(img: np.ndarray, quality: int) -> bytes | None:
    """Encode an image array as an optimized JPEG."""
    params = [
        int(cv2.IMWRITE_JPEG_QUALITY),
        int(quality),
        int(cv2.IMWRITE_JPEG_OPTIMIZE),
        1,
    ]
    ok, encoded = cv2.imencode(".jpg", img, params)
    if ok and encoded is not None:
        return encoded.tobytes()
    return None


def _parse_box(box: Sequence[int | float] | None) -> tuple[int, int, int, int] | None:
    """Validate box as 4 finite numbers [x1, y1, x2, y2] and round to ints."""
    if box is None or isinstance(box, (str, bytes, bytearray)) or not isinstance(box, Sequence):
        return None
    if len(box) != 4:
        return None
    coords: list[int] = []
    for val in box:
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return None
        fval = float(val)
        if not math.isfinite(fval):
            return None
        coords.append(round(fval))
    return coords[0], coords[1], coords[2], coords[3]


def compress_image_bytes(
    image_bytes: bytes | None,
    max_dim: int = 1920,
    quality: int = 75,
) -> bytes | None:
    """Downscale to max_dim if larger and compress as high-clarity JPEG."""
    if not image_bytes:
        return None
    try:
        buf = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w = max(1, round(w * scale))
            new_h = max(1, round(h * scale))
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        encoded = _encode_jpeg(img, quality)
        return encoded if encoded is not None else image_bytes
    except (cv2.error, ValueError, TypeError, OSError):
        return image_bytes


def crop_image_bytes(
    image_bytes: bytes | None,
    box: Sequence[int | float] | None,
    quality: int = 85,
) -> bytes | None:
    """Crop image_bytes to [x1, y1, x2, y2] (clamped to bounds) and encode as JPEG."""
    if not image_bytes:
        return image_bytes
    parsed = _parse_box(box)
    if parsed is None:
        return image_bytes

    try:
        buf = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        h, w = img.shape[:2]
        x1, y1, x2, y2 = parsed
        x1 = max(0, min(w, x1))
        y1 = max(0, min(h, y1))
        x2 = max(0, min(w, x2))
        y2 = max(0, min(h, y2))

        if x2 <= x1 or y2 <= y1:
            return image_bytes

        cropped = img[y1:y2, x1:x2]
        encoded = _encode_jpeg(cropped, quality)
        return encoded if encoded is not None else image_bytes
    except (cv2.error, ValueError, TypeError, OSError):
        return image_bytes
