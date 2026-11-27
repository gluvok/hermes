"""image_compressor.py — High-clarity JPEG compression for fleet camera captures."""
from __future__ import annotations

import io

from PIL import Image, ImageOps


def compress_image_bytes(
    image_bytes: bytes | None,
    max_dim: int = 1920,
    quality: int = 75,
) -> bytes | None:
    """Downscale to max_dim if larger and compress as high-clarity JPEG."""
    if not image_bytes:
        return None
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # reducing_gap=1.0 lets libjpeg-turbo DCT-downscale (draft) before LANCZOS; no-op if already small
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS, reducing_gap=1.0)
            rgb = ImageOps.exif_transpose(img).convert("RGB")  # honour EXIF orientation, as cv2.IMREAD_COLOR did
        out = io.BytesIO()
        rgb.save(out, "JPEG", quality=quality, optimize=True)
        return out.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        return image_bytes
