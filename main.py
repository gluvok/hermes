"""Entrypoint for vehicle image streaming pipeline."""
import asyncio
import signal

from loguru import logger

from src.config import StreamerConfig
from src.image_loader import load_images_to_memory
from src.streamer import run_streamer


async def async_main() -> None:
    cfg = StreamerConfig()
    stop_event = asyncio.Event()

    def handle_signal() -> None:
        logger.info("Shutdown signal received. Stopping streamer...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    images = load_images_to_memory(cfg.data_dir)
    await run_streamer(images, cfg, stop_event)


def main() -> None:
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()
