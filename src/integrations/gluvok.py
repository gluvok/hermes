"""
gluvok.py — Gluvok Cloud API Integration Client
===============================================
Authenticates with the device key in an x-api-key header, sends multipart/form-data
weighment transmission matching the official curl specification (/api/entries/automatic).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from src.config import config
from src.config.constants import (
    CLOUD_MAX_IMAGES,
    CLOUD_POST_RETRIES,
    CLOUD_POST_TIMEOUT,
    GLUVOK_BASE_URL,
)
from src.core.telemetry import (
    record_cloud_auth,
    record_error_event,
    record_system_event,
)

logger = logging.getLogger(__name__)

# POST is safe to retry: the Idempotency-Key makes janus return the original entry on replay.
# Sleeps 0 s, 4 s, 8 s between attempts, or Retry-After when the server sends one (429/503).
_RETRY = Retry(
    total=CLOUD_POST_RETRIES,
    backoff_factor=2,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"POST"}),
    respect_retry_after_header=True,
    raise_on_status=False,  # hand the last response to _parse_cloud_response
)


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

    if len(valid_images) > CLOUD_MAX_IMAGES:
        logger.warning(f"[Gluvok API] {len(valid_images)} images; sending first {CLOUD_MAX_IMAGES}.")
        valid_images = valid_images[:CLOUD_MAX_IMAGES]

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
        record_cloud_auth(accepted=True)
        logger.info(f"[Gluvok API] Entry #{entry_id} created successfully (HTTP {response.status_code})")
        _record_cloud_event("CLOUD", f"Entry #{entry_id} created: {safe_plate} @ {weight:.3f} kg")
        return True, entry_id, None, False

    err_msg = f"HTTP {response.status_code}: {response.text}"
    event_map = {
        401: "CLOUD_AUTH_FAILED",
        403: "CLOUD_AUTH_FORBIDDEN",
        400: "CLOUD_VALIDATION_ERROR",
        429: "CLOUD_RATE_LIMITED",
    }
    if response.status_code in (401, 403):
        record_cloud_auth(accepted=False)
    event_type = event_map.get(response.status_code, "CLOUD_UPLOAD_ERROR")
    _record_cloud_event(event_type, err_msg, is_error=True)
    logger.error(f"[Gluvok API] POST /api/entries/automatic failed {err_msg}")
    return False, None, err_msg, False


def is_validation_rejection(err: str | None) -> bool:
    """True for the HTTP 400 that survived the fallbacks: replaying it can never succeed."""
    return bool(err) and str(err).startswith("HTTP 400:")  # text built in _parse_cloud_response


def transmit_entry_multipart(
    detected_vehicle_number: str,
    weight: float,
    image_bytes: bytes | None = None,
    filename: str = "truck_001.jpg",
    images: list[tuple[str, bytes]] | None = None,
    idempotency_key: str | None = None,
) -> tuple[bool, str | None, str | None, bool]:
    """
    Submits vehicle weighment session to Gluvok API (/api/entries/automatic) matching the curl specification:
      curl -X POST "https://gluvok.vercel.app/api/entries/automatic" \\
        -H "x-api-key: $DEVICE_KEY" \\
        -H "Idempotency-Key: <uuidv7>" \\
        -F "vehicle_number=MH12AB1234" \\
        -F "weight=18540.5" \\
        -F "file=@/home/pi/captures/truck_anpr_1.jpg;type=image/jpeg" \\
        -F "file=@/home/pi/captures/truck_aux_2.jpg;type=image/jpeg" ...
    Pass idempotency_key (a UUIDv7 minted once per weighment) to replay a stored weighment safely;
    without one a fresh key is minted for this call.
    """
    if not config.device_key:  # janus reads only the key; a licence without device_id must still upload
        msg = "Device key (device_key) not configured."
        logger.warning(f"[Gluvok API] POST entry aborted: {msg}")
        _record_cloud_event("CLOUD_AUTH_FAILED", msg, is_error=True)
        return False, None, msg, False

    entries_url = f"{GLUVOK_BASE_URL}/api/entries/automatic"
    # One key per weighment: fallbacks, retries and outbox replays reuse it, so janus never double-counts.
    headers = {"x-api-key": str(config.device_key), "Idempotency-Key": idempotency_key or str(uuid.uuid7())}
    safe_plate = _safe_plate(detected_vehicle_number)
    data = {"vehicle_number": safe_plate, "weight": str(round(weight, 3))}
    files, has_images = _build_multipart_files(images, image_bytes, filename)

    logger.info(
        f"[Gluvok API] Transmitting multipart entry to {entries_url}: "
        f"Vehicle='{safe_plate}', Weight={weight:.3f} kg"
    )

    try:
        # Per-upload session: the retrying adapter is not shared across upload threads.
        with requests.Session() as http:
            http.mount("https://", HTTPAdapter(max_retries=_RETRY))
            http.mount("http://", HTTPAdapter(max_retries=_RETRY))

            def post(form: dict[str, str], parts: list) -> requests.Response:
                return http.post(
                    entries_url, headers=headers, data=form, files=parts,
                    timeout=CLOUD_POST_TIMEOUT, allow_redirects=False,
                )

            response = post(data, files)
            # ponytail: matches janus's zod message text; switch to an error code if janus adds one.
            if (
                response.status_code == 400
                and safe_plate != "NO_PLATE_DETECTED"
                and "vehicle registration" in response.text.lower()
            ):
                logger.warning(
                    f"[Gluvok API] Plate '{safe_plate}' rejected; re-posting as NO_PLATE_DETECTED."
                )
                data = {**data, "vehicle_number": "NO_PLATE_DETECTED"}
                response = post(data, files)
            if response.status_code == 400 and has_images and "storage" in response.text.lower():
                logger.warning(
                    "[Gluvok API] Storage failed on remote server. Retrying without image payload..."
                )
                response = post(data, [("file", (filename, b"", "image/jpeg"))])
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


def package_to_entry(session_payload: dict[str, Any]) -> tuple[str, float, list[tuple[str, bytes]]]:
    """Extracts (plate, weight, images) from a session package; ANPR cameras sort first."""
    plate = _safe_plate(session_payload.get("anpr_plate"))
    weight = float(session_payload.get("weight", 0.0))

    images_to_send: list[tuple[str, bytes]] = []
    fleet_dict = session_payload.get("camera_snapshots", {})
    if isinstance(fleet_dict, dict):
        for cam_name in sorted(fleet_dict.keys()):
            b = fleet_dict[cam_name]
            if b and isinstance(b, bytes):
                images_to_send.append((f"truck_{cam_name}.jpg", b))
    return plate, weight, images_to_send


def post_to_cloud(
    session_payload: dict[str, Any], idempotency_key: str | None = None
) -> tuple[bool, str | None, str | None, bool]:
    """
    Bridge function: transmits entry from session dictionary and updates telemetry.
    Preserved for direct callers; does NOT wipe session_payload on completion.
    """
    plate, weight, images_to_send = package_to_entry(session_payload)
    return transmit_entry_multipart(
        detected_vehicle_number=plate,
        weight=weight,
        images=images_to_send,
        idempotency_key=idempotency_key,
    )


__all__ = [
    "GLUVOK_BASE_URL",
    "is_validation_rejection",
    "package_to_entry",
    "post_to_cloud",
    "transmit_entry_multipart",
]
