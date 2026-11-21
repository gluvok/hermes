"""
gluvok.py — Gluvok Cloud API Integration Client
===============================================
Handles HTTP Basic Authentication (-u device_id:device_key), multipart/form-data
weighment transmission matching the official curl specification (/api/entries).
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from src.config import config
from src.config.constants import CLOUD_POST_TIMEOUT, GLUVOK_BASE_URL
from src.core.telemetry import record_error_event, record_system_event

logger = logging.getLogger(__name__)


_NO_PLATE_VALUES = ("UNKNOWN_PLATE", "UNKNOWN", "NONE", "NULL", "SUCCESS")


def _safe_plate(value: object) -> str:
    """Normalise a plate string; placeholder or empty values become NO_PLATE_DETECTED."""
    plate = str(value or "NO_PLATE_DETECTED").strip().upper()
    return "NO_PLATE_DETECTED" if not plate or plate in _NO_PLATE_VALUES else plate


def _record_cloud_event(event_type: str, message: str, is_error: bool = False) -> None:
    """Safely logs system and error events to the core telemetry store."""
    if is_error:
        record_error_event(event_type, message)
        record_system_event("CLOUD", f"Upload error ({event_type}): {message}")
    else:
        record_system_event(event_type, message)


def _build_multipart_files(
    images: list[tuple[str, bytes]] | None,
    image_bytes: bytes | None,
    filename: str,
) -> tuple[list[tuple[str, tuple[str, bytes, str]]], bool]:
    # Inputs are already compressed in session.py; send them as-is (no second lossy re-encode).
    valid_images: list[tuple[str, bytes]] = []
    if images:
        for fname, b in images:
            if b and isinstance(b, bytes) and len(b) > 0:
                valid_images.append((fname, b))

    if not valid_images and image_bytes and isinstance(image_bytes, bytes) and len(image_bytes) > 0:
        valid_images.append((filename, image_bytes))

    if valid_images:
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            ("file", (fn, b, "image/jpeg")) for fn, b in valid_images
        ]
        return files, True
    return [("file", (filename, b"", "image/jpeg"))], False


def _parse_cloud_response(
    response: requests.Response, safe_plate: str, weight: float
) -> tuple[bool, str | None, str | None, bool]:
    if response.status_code in (200, 201):
        res_data = response.json() if response.content else {}
        entry_id = str(res_data.get("data", {}).get("id") or res_data.get("id") or "N/A")
        logger.info(f"[Gluvok API] Entry #{entry_id} created successfully (HTTP {response.status_code})")
        _record_cloud_event("CLOUD", f"Entry #{entry_id} created: {safe_plate} @ {weight:.3f} kg")
        return True, entry_id, None, False

    err_msg = f"HTTP {response.status_code}: {response.text}"
    event_map = {
        401: "CLOUD_AUTH_FAILED",
        403: "CLOUD_AUTH_FORBIDDEN",
        400: "CLOUD_VALIDATION_ERROR",
    }
    event_type = event_map.get(response.status_code, "CLOUD_UPLOAD_ERROR")
    _record_cloud_event(event_type, err_msg, is_error=True)
    logger.error(f"[Gluvok API] POST /api/entries failed {err_msg}")
    return False, None, err_msg, False


def transmit_entry_multipart(
    center_id: int,
    detected_vehicle_number: str,
    weight: float,
    image_bytes: bytes | None = None,
    filename: str = "truck_001.jpg",
    images: list[tuple[str, bytes]] | None = None,
) -> tuple[bool, str | None, str | None, bool]:
    """
    Submits vehicle weighment session to Gluvok API (/api/entries) matching the curl specification:
      curl -X POST "https://gluvok.vercel.app/api/entries" \\
        -u "$DEVICE_ID:$DEVICE_KEY" \\
        -F "center_id=1" \\
        -F "detected_vehicle_number=MH12AB1234" \\
        -F "weight=18540.5" \\
        -F "file=@/home/pi/captures/truck_anpr_1.jpg;type=image/jpeg" \\
        -F "file=@/home/pi/captures/truck_aux_2.jpg;type=image/jpeg" ...
    """
    if not config.device_id or not config.device_key:
        msg = "Device credentials (device_id, device_key) not configured."
        logger.warning(f"[Gluvok API] POST entry aborted: {msg}")
        _record_cloud_event("CLOUD_AUTH_FAILED", msg, is_error=True)
        return False, None, msg, False

    entries_url = f"{GLUVOK_BASE_URL}/api/entries"
    auth = (str(config.device_id), config.device_key)
    safe_plate = _safe_plate(detected_vehicle_number)
    data = {
        "center_id": str(center_id),
        "detected_vehicle_number": safe_plate,
        "weight": str(round(weight, 3)),
    }
    files, has_images = _build_multipart_files(images, image_bytes, filename)

    logger.info(
        f"[Gluvok API] Transmitting multipart entry to {entries_url}: "
        f"Vehicle='{safe_plate}', Weight={weight:.3f} kg, Center ID={center_id}"
    )

    try:
        response = requests.post(
            entries_url, auth=auth, data=data, files=files, timeout=CLOUD_POST_TIMEOUT
        )
        if response.status_code == 400 and has_images and "storage" in response.text.lower():
            logger.warning(
                "[Gluvok API] Storage failed on remote server. Retrying without image payload..."
            )
            fallback_files = [("file", (filename, b"", "image/jpeg"))]
            response = requests.post(
                entries_url, auth=auth, data=data, files=fallback_files, timeout=CLOUD_POST_TIMEOUT
            )
        return _parse_cloud_response(response, safe_plate, weight)

    except requests.exceptions.ReadTimeout as e:
        err_msg = f"ReadTimeout: {e}"
        logger.warning(f"[Gluvok API] Read timeout awaiting response from server: {err_msg}")
        _record_cloud_event("CLOUD_UPLOAD_ERROR", err_msg, is_error=True)
        return False, None, err_msg, True

    except (requests.RequestException, OSError, ValueError) as e:
        err_msg = f"{type(e).__name__}: {e}"
        logger.error(f"[Gluvok API] Network exception during transmission: {err_msg}")
        _record_cloud_event("CLOUD_UPLOAD_ERROR", err_msg, is_error=True)
        return False, None, err_msg, False


def post_to_cloud(session_payload: dict[str, Any]) -> tuple[bool, str | None, str | None, bool]:
    """
    Bridge function: transmits entry from session dictionary and updates telemetry.
    Preserved for direct callers; does NOT wipe session_payload on completion.
    """
    center_id = int(config.center_id)
    plate = _safe_plate(session_payload.get("anpr_plate"))
    weight = float(session_payload.get("weight", 0.0))

    images_to_send: list[tuple[str, bytes]] = []
    fleet_dict = session_payload.get("camera_snapshots", {})
    if isinstance(fleet_dict, dict):
        for cam_name in sorted(fleet_dict.keys()):
            b = fleet_dict[cam_name]
            if b and isinstance(b, bytes):
                images_to_send.append((f"truck_{cam_name}.jpg", b))

    return transmit_entry_multipart(
        center_id=center_id,
        detected_vehicle_number=plate,
        weight=weight,
        images=images_to_send,
    )


__all__ = [
    "GLUVOK_BASE_URL",
    "post_to_cloud",
    "transmit_entry_multipart",
]
