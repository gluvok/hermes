"""Unit tests for streamer configuration dataclass."""
import dataclasses
from pathlib import Path

import pytest

from src.config import StreamerConfig


def test_streamer_config_defaults() -> None:
    cfg = StreamerConfig()
    assert cfg.server_url == "http://127.0.0.1:8000/recognize"
    assert cfg.data_dir == Path("data")
    assert cfg.batch_size == 2
    assert cfg.interval_sec == 0.5
    assert cfg.max_concurrency == 8
    assert cfg.timeout_sec == 10.0


def test_streamer_config_frozen() -> None:
    cfg = StreamerConfig()
    attr_name = "batch_size"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(cfg, attr_name, 5)
