"""
anpr.py — Argus ANPR Microservice REST Client
=============================================
Sends raw JPEG frames to the Argus ANPR endpoint (/recognize), parses plate results,
and computes consensus vehicle plate numbers via frequency counting.
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Literal, overload

import requests

from src.config import config
from src.config.constants import ANPR_SERVER_TIMEOUT

logger = logging.getLogger(__name__)


def resolve_anpr_endpoint(url: str | None = None) -> str:
    """Resolves ANPR server URL, replacing 0.0.0.0 with 127.0.0.1 and appending /recognize if omitted."""
    raw = (url or config.anpr_server_url or "http://127.0.0.1:8000/recognize").strip()
    raw = raw.replace("://0.0.0.0", "://127.0.0.1")
    raw = raw.rstrip("/")
    if not raw.endswith("/recognize"):
        raw = f"{raw}/recognize"
    return raw


def _normalize_plate_value(plate_val: object) -> str | None:
    """Return a cleaned plate string, or None if the value is empty/N/A."""
    if not plate_val or not isinstance(plate_val, str):
        return None
    plate_clean = plate_val.strip().upper()
    if not plate_clean or plate_clean == "N/A":
        return None
    return plate_clean


def _plate_from_flat_keys(data: dict) -> tuple[str, str] | None:
    """Extract plate from flat JSON keys used by generic ANPR responses."""
    for key in ("plate", "number_plate", "plate_number", "text", "result"):
        plate_clean = _normalize_plate_value(data.get(key))
        if plate_clean:
            logger.info(f"[ANPR] Server returned plate: '{plate_clean}' (key='{key}')")
            return plate_clean, "SUCCESS"
    return None


def _extract_plate_from_dict(
    data: dict,
) -> tuple[str | None, str, tuple[int, int, int, int] | None]:
    """
    Extract plate string, status code, and vehicle bounding box from Argus response.
    """
    if "results" in data:
        results = data.get("results")
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            if isinstance(first, dict):
                plate_clean = _normalize_plate_value(first.get("plate"))
                raw_box = first.get("vehicle_box")
                vbox: tuple[int, int, int, int] | None = (
                    (int(raw_box[0]), int(raw_box[1]), int(raw_box[2]), int(raw_box[3]))
                    if raw_box and len(raw_box) >= 4
                    else None
                )
                if plate_clean:
                    vtype = first.get("vehicle_type") or "vehicle"
                    conf = first.get("confidence")
                    conf_str = (
                        f", conf={conf:.4f}" if isinstance(conf, (int, float)) else ""
                    )
                    logger.info(
                        f"[ANPR] Argus best plate: '{plate_clean}' ({vtype}{conf_str})"
                    )
                    return plate_clean, "SUCCESS", vbox
        logger.info("[ANPR] Argus returned empty or unreadable results list.")
        return None, "NO_PLATE_DETECTED", None

    # Fallback for generic/flat JSON endpoints: {"plate": "..."}
    from_flat = _plate_from_flat_keys(data)
    if from_flat is not None:
        return from_flat[0], from_flat[1], None

    return None, "NO_PLATE_DETECTED", None


def _parse_anpr_response(
    response: requests.Response, elapsed_ms: float = 0.0
) -> tuple[str | None, str, tuple[int, int, int, int] | None]:
    """Parses HTTP response body from ANPR microservice."""
    raw_body = response.text.strip()
    latency_str = f" in {elapsed_ms:.1f}ms" if elapsed_ms > 0 else ""
    if response.status_code in (200, 201):
        try:
            data = response.json()
            formatted_json = json.dumps(data, indent=2)
            logger.info(
                f"[ANPR] [Argus Response] Status {response.status_code}{latency_str}:\n{formatted_json}"
            )
            if isinstance(data, dict):
                return _extract_plate_from_dict(data)
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                return _extract_plate_from_dict(data[0])
            elif isinstance(data, str) and data.strip():
                return data.strip().upper(), "SUCCESS", None
        except (ValueError, KeyError, json.JSONDecodeError, TypeError) as parse_err:
            logger.info(
                f"[ANPR] [Argus Response] Status {response.status_code}{latency_str}: {raw_body}"
            )
            text = raw_body.upper()
            if text and text != "N/A":
                logger.info(f"[ANPR] Server returned text response: '{text}'")
                return text, "SUCCESS", None
            logger.warning(f"[ANPR] Failed to parse server response: {parse_err}")
    else:
        logger.info(
            f"[ANPR] [Argus Response] Status {response.status_code}{latency_str}: {raw_body}"
        )

    error_code = f"ANPR_HTTP_{response.status_code}"
    logger.warning(
        f"[ANPR] Server POST status {response.status_code}: {raw_body[:120]}"
    )
    return None, error_code, None


AnprRecordCallback = Callable[..., Any]


@overload
def send_frame_to_anpr_server(
    image_bytes: bytes | None,
    server_url: str | None = None,
    timeout: float = ANPR_SERVER_TIMEOUT,
    session: requests.Session | None = None,
    return_details: Literal[False] = False,
) -> tuple[str | None, str]: ...


@overload
def send_frame_to_anpr_server(
    image_bytes: bytes | None,
    server_url: str | None = None,
    timeout: float = ANPR_SERVER_TIMEOUT,
    session: requests.Session | None = None,
    return_details: Literal[True] = True,
) -> tuple[str | None, str, tuple[int, int, int, int] | None]: ...


def send_frame_to_anpr_server(
    image_bytes: bytes | None,
    server_url: str | None = None,
    timeout: float = ANPR_SERVER_TIMEOUT,
    session: requests.Session | None = None,
    return_details: bool = False,
) -> tuple[str | None, str] | tuple[str | None, str, tuple[int, int, int, int] | None]:
    """Sends raw JPEG image bytes to the Argus ANPR FastAPI microservice (/recognize)."""
    if not image_bytes:
        logger.warning("[ANPR] Cannot send image to Argus: frame bytes empty/None.")
        return (None, "EMPTY_IMAGE", None) if return_details else (None, "EMPTY_IMAGE")

    target_url = resolve_anpr_endpoint(server_url)
    logger.info(f"[ANPR] POST image ({len(image_bytes)} bytes) -> {target_url}")
    start_time = time.time()
    try:
        files = {"file": ("frame.jpg", image_bytes, "image/jpeg")}
        if session is not None:
            response = session.post(target_url, files=files, timeout=timeout)
        else:
            response = requests.post(target_url, files=files, timeout=timeout)
        elapsed_ms = (time.time() - start_time) * 1000.0
        plate, status_code, vbox = _parse_anpr_response(response, elapsed_ms=elapsed_ms)
        return (plate, status_code, vbox) if return_details else (plate, status_code)
    except requests.exceptions.Timeout:
        logger.warning(
            f"[ANPR] Timeout ({timeout}s) contacting ANPR server at {target_url}"
        )
        return (
            (None, "ANPR_TIMEOUT", None) if return_details else (None, "ANPR_TIMEOUT")
        )
    except requests.exceptions.ConnectionError:
        logger.warning(
            f"[ANPR] Failed to connect to ANPR server at {target_url}. Is Argus running?"
        )
        return (
            (None, "ANPR_CONNECTION_ERROR", None)
            if return_details
            else (None, "ANPR_CONNECTION_ERROR")
        )
    except requests.RequestException as e:
        logger.error(
            f"[ANPR] Exception submitting frame to ANPR server ({target_url}): {e}"
        )
        return (
            (None, "ANPR_REQUEST_ERROR", None)
            if return_details
            else (None, "ANPR_REQUEST_ERROR")
        )


def send_and_record_anpr_frame(
    session_id: str,
    cam_idx: int,
    image_bytes: bytes,
    server_url: str | None = None,
    callback: AnprRecordCallback | None = None,
    session: requests.Session | None = None,
    sender: Callable[..., Any] | None = None,
) -> tuple[str | None, str]:
    """Execute ANPR request for a single camera frame and invoke record callback."""
    sender_fn = sender or send_frame_to_anpr_server
    logger.info(
        f"[ANPR] Camera {cam_idx}: Dispatching image ({len(image_bytes)} bytes) "
        f"for session {session_id} to Argus..."
    )
    t0 = time.time()
    vehicle_box = None
    try:
        res = None
        if session is not None or server_url is not None:
            try:
                res = sender_fn(
                    image_bytes,
                    server_url=server_url,
                    session=session,
                    return_details=True,
                )
            except TypeError:
                try:
                    res = sender_fn(image_bytes, server_url=server_url, session=session)
                except TypeError:
                    res = sender_fn(image_bytes)
        else:
            try:
                res = sender_fn(image_bytes, return_details=True)
            except TypeError:
                res = sender_fn(image_bytes)

        if isinstance(res, tuple) and len(res) >= 3:
            plate, status_code, vehicle_box = res[0], res[1], res[2]
        elif isinstance(res, tuple) and len(res) >= 2:
            plate, status_code = res[0], res[1]
        else:
            plate, status_code = None, "ANPR_RESPONSE_ERROR"
    except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
        logger.error(
            f"[ANPR] Worker error for session {session_id} cam {cam_idx}: {exc}"
        )
        plate, status_code, vehicle_box = None, "ANPR_WORKER_ERROR", None

    elapsed_ms = (time.time() - t0) * 1000.0
    if plate:
        logger.info(
            f"[ANPR] Camera {cam_idx} (Session {session_id}): Plate detected: '{plate}' "
            f"(Status={status_code}, Elapsed={elapsed_ms:.1f}ms)"
        )
    else:
        logger.info(
            f"[ANPR] Camera {cam_idx} (Session {session_id}): No plate detected "
            f"(Status={status_code}, Elapsed={elapsed_ms:.1f}ms)"
        )

    if callback is not None:
        try:
            try:
                callback(
                    session_id,
                    cam_idx,
                    plate,
                    status_code,
                    vehicle_box=vehicle_box,
                )
            except TypeError:
                callback(session_id, cam_idx, plate, status_code)
        except (ValueError, KeyError, RuntimeError, TypeError) as exc:
            logger.error(f"[ANPR] Callback error for session {session_id}: {exc}")

    return plate, status_code


def dispatch_anpr_batch(
    pool: ThreadPoolExecutor,
    session_id: str,
    batch: Sequence[tuple[int, bytes]],
    server_url: str | None = None,
    callback: AnprRecordCallback | None = None,
    session: requests.Session | None = None,
    sender: Callable[..., tuple[str | None, str]] | None = None,
) -> list[Future[tuple[str | None, str]]]:
    """Submit a batch of ANPR camera frames concurrently to the worker pool."""
    futures: list[Future[tuple[str | None, str]]] = []
    for cam_idx, img_bytes in batch:
        if not img_bytes:
            continue
        future = pool.submit(
            send_and_record_anpr_frame,
            session_id,
            cam_idx,
            img_bytes,
            server_url,
            callback,
            session,
            sender,
        )
        futures.append(future)
    return futures


def get_highest_frequency_plate(plate_list: Sequence[str | None]) -> str:
    """
    Analyzes a list of plate reading strings collected during a session and returns
    the string with the highest frequency.
    Returns 'NO_PLATE_DETECTED' if no valid plate was recognized.
    """
    valid_plates = [
        p.strip().upper() for p in plate_list if p and isinstance(p, str) and p.strip()
    ]

    if not valid_plates:
        logger.warning("[ANPR Voting] No valid plates recorded during session.")
        return "NO_PLATE_DETECTED"

    counter = Counter(valid_plates)
    most_common_plate, count = counter.most_common(1)[0]
    total_samples = len(valid_plates)

    logger.info(
        f"[ANPR Voting] Winner: '{most_common_plate}' "
        f"(Frequency: {count}/{total_samples}, All candidates: {dict(counter)})"
    )
    return most_common_plate


__all__ = [
    "dispatch_anpr_batch",
    "get_highest_frequency_plate",
    "resolve_anpr_endpoint",
    "send_and_record_anpr_frame",
    "send_frame_to_anpr_server",
]
