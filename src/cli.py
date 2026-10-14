"""Command line interface parsing for Hermes vehicle image streamer."""
import argparse
from pathlib import Path

from src.config import StreamerConfig


def parse_args(args: list[str] | None = None) -> StreamerConfig:
    parser = argparse.ArgumentParser(
        description="Hermes Vehicle Image Streamer"
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000/recognize")
    parser.add_argument("--dir", default="data", type=Path)
    parser.add_argument("--db", default="data/vehicles.db", type=Path)
    parser.add_argument("--batch-size", default=2, type=int)
    parser.add_argument("--interval", default=0.5, type=float)
    parser.add_argument("--once", action="store_true", help="Stop after 1 pass")
    parsed = parser.parse_args(args)
    return StreamerConfig(
        server_url=parsed.url,
        data_dir=parsed.dir,
        db_path=parsed.db,
        batch_size=parsed.batch_size,
        interval_sec=parsed.interval,
        loop=not parsed.once,
    )
