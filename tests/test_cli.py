"""Unit tests for CLI argument parsing."""
from pathlib import Path

from src.cli import parse_args


def test_parse_args_defaults() -> None:
    cfg = parse_args([])
    assert cfg.server_url == "http://127.0.0.1:8000/recognize"
    assert cfg.data_dir == Path("data")
    assert cfg.db_path == Path("data/vehicles.db")
    assert cfg.batch_size == 2
    assert cfg.interval_sec == 0.5
    assert cfg.loop is True


def test_parse_args_custom() -> None:
    cfg = parse_args([
        "--url",
        "http://custom:9000/test",
        "--dir",
        "custom_dir",
        "--db",
        "custom.db",
        "--batch-size",
        "4",
        "--interval",
        "1.0",
        "--once",
    ])
    assert cfg.server_url == "http://custom:9000/test"
    assert cfg.data_dir == Path("custom_dir")
    assert cfg.db_path == Path("custom.db")
    assert cfg.batch_size == 4
    assert cfg.interval_sec == 1.0
    assert cfg.loop is False
