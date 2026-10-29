"""Paced asynchronous in-memory image streaming scheduler."""
import asyncio
from typing import Any

import httpx
from loguru import logger

from src.client import send_image
from src.config import StreamerConfig
from src.image_loader import InMemoryImage

type AsyncTaskSet = set[asyncio.Task[Any]]


def cancel_active_tasks(tasks: AsyncTaskSet) -> None:
    for task in tasks:
        if not task.done():
            task.cancel()


async def run_streamer(
    images: list[InMemoryImage],
    cfg: StreamerConfig,
    stop_event: asyncio.Event,
) -> None:
    if not images:
        logger.warning("No images available in RAM to stream.")
        return

    cursor, total = 0, len(images)
    sem = asyncio.Semaphore(cfg.max_concurrency)
    active_tasks: AsyncTaskSet = set()
    async with httpx.AsyncClient(timeout=cfg.timeout_sec) as client:
        logger.info(
            f"Streaming {total} images from RAM (batch={cfg.batch_size}, "
            f"interval={cfg.interval_sec:.1f}s)"
        )
        while not stop_event.is_set():
            if cursor >= total:
                if not cfg.loop:
                    logger.info("Reached end of RAM dataset. Stopping.")
                    break
                cursor = 0

            batch = images[cursor : cursor + cfg.batch_size]
            cursor += len(batch)
            for img in batch:
                task = asyncio.create_task(
                    send_image(client, cfg.server_url, img, sem)
                )
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=cfg.interval_sec)
            except TimeoutError:
                pass

        cancel_active_tasks(active_tasks)
