"""Entrypoint for vehicle image streaming pipeline."""
import signal
from threading import Event

from loguru import logger

from src.cli import parse_args
from src.database import DatabaseManager
from src.image_loader import load_images_to_memory
from src.streamer import run_streamer


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
