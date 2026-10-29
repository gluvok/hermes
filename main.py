"""Entrypoint for vehicle image streaming pipeline."""
import asyncio

from src.config import StreamerConfig
from src.image_loader import load_images_to_memory
from src.streamer import run_streamer


async def async_main() -> None:
    cfg = StreamerConfig()
    images = load_images_to_memory(cfg.data_dir)
    await run_streamer(images, cfg)


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
