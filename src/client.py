"""HTTP client for async vehicle recognition requests."""
import asyncio
from typing import Any

import httpx
from loguru import logger

from src.image_loader import InMemoryImage

type RecognitionPayload = dict[str, Any]
type VehicleNumber = str | None


def extract_first_plate(result: RecognitionPayload) -> VehicleNumber:
    results = result.get("results")
    if isinstance(results, list) and results and "plate" in results[0]:
        return str(results[0]["plate"])
    return None


async def send_image(
    client: httpx.AsyncClient,
    server_url: str,
    img: InMemoryImage,
    sem: asyncio.Semaphore,
) -> RecognitionPayload | None:
    async with sem:
        try:
            files = {"file": (img.name, img.data, "image/jpeg")}
            response = await client.post(server_url, files=files)
            response.raise_for_status()
            result: RecognitionPayload = response.json()
            first_plate = extract_first_plate(result)
            plate_display = first_plate if first_plate is not None else "NONE"
            logger.info(f"[{img.name}] Plate: {plate_display}")
            return result
        except (httpx.HTTPError, OSError) as exc:
            logger.error(f"[{img.name}] Request failed: {exc}")
            return None
