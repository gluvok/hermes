"""Paced asynchronous in-memory image streaming scheduler."""
import asyncio

import httpx
from loguru import logger

from src.client import RecognitionPayload, send_image
from src.config import StreamerConfig
from src.image_loader import InMemoryImage


async def run_streamer(
    images: list[InMemoryImage],
    cfg: StreamerConfig,
) -> list[RecognitionPayload | None]:
    if not images:
        logger.warning("No images available in RAM to stream.")
        return []

    total = len(images)
    sem = asyncio.Semaphore(cfg.max_concurrency)
    tasks: list[asyncio.Task[RecognitionPayload | None]] = []
    async with httpx.AsyncClient(timeout=cfg.timeout_sec) as client:
        logger.info(
            f"Streaming {total} images from RAM (batch={cfg.batch_size}, "
            f"interval={cfg.interval_sec:.1f}s)"
        )
        for i in range(0, total, cfg.batch_size):
            batch = images[i : i + cfg.batch_size]
            for img in batch:
                tasks.append(
                    asyncio.create_task(
                        send_image(client, cfg.server_url, img, sem)
                    )
                )
            await asyncio.sleep(cfg.interval_sec)

        return list(await asyncio.gather(*tasks, return_exceptions=False))
