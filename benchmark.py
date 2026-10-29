"""Entrypoint for vehicle recognition benchmarking and latency reporting."""
import asyncio

from src.config import StreamerConfig
from src.image_loader import load_images_to_memory
from src.reporter import compute_report, log_report
from src.streamer import run_streamer


async def async_main() -> None:
    cfg = StreamerConfig()
    images = load_images_to_memory(cfg.data_dir)
    results = await run_streamer(images, cfg)
    log_report(compute_report(results))


asyncio.run(async_main())

