"""Entrypoint for vehicle image streaming pipeline."""
import argparse
import signal
from pathlib import Path
from threading import Event

from loguru import logger

from src.config import StreamerConfig
from src.database import DatabaseManager
from src.image_loader import load_images_to_memory
from src.streamer import run_streamer


def parse_args() -> StreamerConfig:
    parser = argparse.ArgumentParser(
        description="Hermes Vehicle Image Streamer"
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000/recognize")
    parser.add_argument("--dir", default="data", type=Path)
    parser.add_argument("--db", default="data/vehicles.db", type=Path)
    parser.add_argument("--batch-size", default=2, type=int)
    parser.add_argument("--interval", default=0.5, type=float)
    parser.add_argument("--once", action="store_true", help="Stop after 1 pass")
    args = parser.parse_args()
    return StreamerConfig(
        server_url=args.url,
        data_dir=args.dir,
        db_path=args.db,
        batch_size=args.batch_size,
        interval_sec=args.interval,
        loop=not args.once,
    )


def main() -> None:
    cfg = parse_args()
    db = DatabaseManager(cfg.db_path)
    stop_event = Event()

    def handle_signal(_signum: int, _frame: object) -> None:
        logger.info("Shutdown signal received. Stopping streamer...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    images = load_images_to_memory(cfg.data_dir)
    run_streamer(images, cfg, db, stop_event)


if __name__ == "__main__":
    main()
