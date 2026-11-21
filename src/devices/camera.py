"""
camera.py — IP Camera Frame Grabber & Parallel Snapshot Driver
==============================================================
Low-resource IP camera frame capture module.
Supports HTTP JPEG Snapshots and on-demand OpenCV RTSP stream frame grabbing.
Uses ThreadPoolExecutor for concurrent multi-camera snapshot capture.
"""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import requests
import urllib3

from src.config import config
from src.config.constants import (
    CAMERA_TIMEOUT,
    MAX_PARALLEL_CAMERA_WORKERS,
)

logger = logging.getLogger(__name__)

# LAN cameras with self-signed certs; TLS verification deliberately off (see verify=False below)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_URL_CREDS = re.compile(r"//[^/@\s]+@")


def _mask(text: object) -> str:
    """Hide user:pass@ in camera URLs (and exception text containing them) before logging."""
    return _URL_CREDS.sub("//***@", str(text))


def fetch_image_bytes(camera_url: str, timeout: float = CAMERA_TIMEOUT) -> bytes | None:
    """
    Fetch raw JPEG image bytes from a camera URL.
    Prefers HTTP JPEG Snapshots for low CPU/RAM footprint.
    Falls back to on-demand OpenCV RTSP single-frame capture if URL starts with 'rtsp://'.
    """
    if not camera_url:
        return None

    if camera_url.lower().startswith("rtsp://"):
        return _fetch_rtsp_frame(camera_url, timeout)
    else:
        return _fetch_http_snapshot(camera_url, timeout)


def _fetch_http_snapshot(url: str, timeout: float) -> bytes | None:
    """Fetch HTTP JPEG snapshot with low memory footprint."""
    try:
        # LAN cameras with self-signed certs; TLS verification deliberately off
        response = requests.get(url, timeout=timeout, verify=False)
        if response.status_code == 200 and response.content:
            return response.content
        else:
            logger.warning(f"[Camera] HTTP fetch failed for {_mask(url)}: Status {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"[Camera] Exception fetching snapshot from {_mask(url)}: {_mask(e)}")
        return None


def _fetch_rtsp_frame(rtsp_url: str, timeout: float) -> bytes | None:
    """On-demand single frame capture from RTSP stream using OpenCV."""
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            logger.warning(f"[Camera] Unable to open RTSP stream: {_mask(rtsp_url)}")
            return None

        # Set low buffer size if supported
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            # Encode frame to JPEG byte buffer in RAM
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if success:
                return buffer.tobytes()
        logger.warning(f"[Camera] Failed to read frame from RTSP stream: {_mask(rtsp_url)}")
        return None
    except (cv2.error, OSError, ValueError) as e:
        logger.error(f"[Camera] OpenCV RTSP exception for {_mask(rtsp_url)}: {_mask(e)}")
        return None


def capture_anpr_snapshots(
    camera_urls: list[str] | None = None,
) -> list[tuple[int, str, bytes | None]]:
    """
    Concurrently captures snapshot images from all configured ANPR cameras (e.g. Front, Rear).
    Returns a list of tuples: (camera_index, camera_url, image_bytes_or_none).
    Camera index is 1-based (1 for Front ANPR, 2 for Rear ANPR, etc.)
    """
    urls = camera_urls if camera_urls is not None else config.anpr_camera_urls
    if not urls:
        return []

    if len(urls) == 1:
        img_bytes = fetch_image_bytes(urls[0])
        return [(1, urls[0], img_bytes)]

    workers = min(len(urls), MAX_PARALLEL_CAMERA_WORKERS)
    results_dict: dict[int, bytes | None] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(fetch_image_bytes, url): idx + 1
            for idx, url in enumerate(urls)
        }
        for future in as_completed(future_to_idx):
            cam_idx = future_to_idx[future]
            try:
                results_dict[cam_idx] = future.result()
            except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
                logger.error(f"[Camera] ANPR Camera {cam_idx} generated exception: {_mask(exc)}")
                results_dict[cam_idx] = None

    return [(idx + 1, url, results_dict.get(idx + 1)) for idx, url in enumerate(urls)]


def capture_all_camera_snapshots(
    anpr_urls: list[str] | None = None,
    aux_urls: list[str] | None = None,
) -> dict[str, bytes | None]:
    """
    Concurrently captures snapshots from all cameras (all ANPR + all Auxiliary).
    Returns a dict mapping canonical labels ('anpr_1', 'anpr_2', 'aux_1', 'aux_2', etc.)
    to raw JPEG bytes or None.
    """
    a_urls = anpr_urls if anpr_urls is not None else config.anpr_camera_urls
    x_urls = aux_urls if aux_urls is not None else config.auxiliary_camera_urls

    labeled_tasks: list[tuple[str, str]] = []
    for idx, url in enumerate(a_urls):
        labeled_tasks.append((f"anpr_{idx + 1}", url))
    for idx, url in enumerate(x_urls):
        labeled_tasks.append((f"aux_{idx + 1}", url))

    if not labeled_tasks:
        return {}

    workers = min(len(labeled_tasks), MAX_PARALLEL_CAMERA_WORKERS)
    results: dict[str, bytes | None] = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_label = {
            executor.submit(fetch_image_bytes, url): label
            for label, url in labeled_tasks
        }
        for future in as_completed(future_to_label):
            label = future_to_label[future]
            try:
                img_bytes = future.result()
                results[label] = img_bytes
                status = "SUCCESS" if img_bytes else "FAILED"
                logger.info(f"[Camera] Full fleet {label} capture: {status}")
            except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
                logger.error(f"[Camera] {label} snapshot generated exception: {_mask(exc)}")
                results[label] = None

    elapsed = time.time() - start_time
    logger.info(f"[Camera] Full fleet capture ({len(labeled_tasks)} cameras) completed in {elapsed:.2f}s")
    return results


def log_camera_fleet() -> None:
    """Logs the configured main (ANPR) and auxiliary camera fleet at startup."""
    anpr_urls = config.anpr_camera_urls
    aux_urls = config.auxiliary_camera_urls

    logger.info("[Cameras] Configured Camera Fleet:")
    if anpr_urls:
        logger.info(f"  ├── Main / ANPR Cameras ({len(anpr_urls)} configured - active loop):")
        for idx, url in enumerate(anpr_urls):
            prefix = "└──" if idx == len(anpr_urls) - 1 and not aux_urls else "├──"
            logger.info(f"  │     {prefix} [Cam {idx + 1} - ANPR] {_mask(url)}")
    else:
        logger.warning("  ├── Main / ANPR Cameras: (None configured)")

    if aux_urls:
        logger.info(f"  └── Auxiliary Cameras ({len(aux_urls)} configured - post-stability audit):")
        for idx, url in enumerate(aux_urls):
            prefix = "└──" if idx == len(aux_urls) - 1 else "├──"
            logger.info(f"        {prefix} [Aux {idx + 1}] {_mask(url)}")
    else:
        logger.info("  └── Auxiliary Cameras: (None configured)")


__all__ = [
    "capture_all_camera_snapshots",
    "capture_anpr_snapshots",
    "fetch_image_bytes",
    "log_camera_fleet",
]
