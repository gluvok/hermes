"""Paced asynchronous in-memory image streaming scheduler."""
import asyncio

import httpx
from loguru import logger

from src.client import send_image
from src.config import StreamerConfig
from src.image_loader import InMemoryImage


async def run_streamer(
    images: list[InMemoryImage],
    cfg: StreamerConfig,
) -> None:
    if not images:
        logger.warning("No images available in RAM to stream.")
        return

    cursor, total = 0, len(images)
    sem = asyncio.Semaphore(cfg.max_concurrency)
    async with httpx.AsyncClient(timeout=cfg.timeout_sec) as client:
        logger.info(
            f"Streaming {total} images from RAM (batch={cfg.batch_size}, "
            f"interval={cfg.interval_sec:.1f}s)"
        )
        while True:
            if cursor >= total:
                if not cfg.loop:
                    logger.info("Reached end of RAM dataset. Stopping.")
                    break
                cursor = 0

            batch = images[cursor : cursor + cfg.batch_size]
            cursor += len(batch)
            for img in batch:
                asyncio.create_task(
                    send_image(client, cfg.server_url, img, sem)
                )

            await asyncio.sleep(cfg.interval_sec)
