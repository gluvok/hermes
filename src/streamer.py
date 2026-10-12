"""Paced multithreaded in-memory image streaming scheduler."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
from loguru import logger

from src.client import send_and_record_image
from src.config import StreamerConfig
from src.database import DatabaseManager
from src.image_loader import InMemoryImage


def run_streamer(
    images: list[InMemoryImage],
    cfg: StreamerConfig,
    db: DatabaseManager,
    stop_event: Event,
) -> None:
    if not images:
        logger.warning("No images available in RAM to stream.")
        return

    cursor = 0
    total = len(images)

    with (
        httpx.Client(timeout=cfg.timeout_sec) as client,
        ThreadPoolExecutor(max_workers=cfg.max_workers) as pool,
    ):
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
                pool.submit(
                    send_and_record_image, client, cfg.server_url, img, db
                )

            stop_event.wait(cfg.interval_sec)
