"""HTTP client for recognition requests and SQLite persistence."""
from typing import Any

import httpx
from loguru import logger

from src.database import DatabaseManager
from src.image_loader import InMemoryImage


def extract_first_plate(result: dict[str, Any]) -> str | None:
    results = result.get("results")
    if isinstance(results, list) and results and "plate" in results[0]:
        return str(results[0]["plate"])
    return None


def send_and_record_image(
    client: httpx.Client,
    server_url: str,
    img: InMemoryImage,
    db: DatabaseManager,
) -> dict[str, Any] | None:
    try:
        files = {"file": (img.name, img.data, "image/jpeg")}
        response = client.post(server_url, files=files)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        first_plate = extract_first_plate(result)
        db.save_detection(img.name, first_plate, img.data)
        plate_display = first_plate if first_plate is not None else "NONE"
        logger.info(f"[{img.name}] Plate: {plate_display} | Saved to DB")
        return result
    except (httpx.HTTPError, OSError) as exc:
        logger.error(f"[{img.name}] Request failed: {exc}")
        return None
