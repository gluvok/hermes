"""Configuration settings for image streaming."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StreamerConfig:
    server_url: str = "http://127.0.0.1:8000/recognize"
    data_dir: Path = Path("data")
    db_path: Path = Path("data/vehicles.db")
    batch_size: int = 2
    interval_sec: float = 0.5
    loop: bool = True
    max_workers: int = 8
    timeout_sec: float = 10.0
