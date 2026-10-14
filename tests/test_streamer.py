"""Unit tests for vehicle image streamer scheduling and batch dispatch."""
from threading import Event
from unittest import mock

from src.config import StreamerConfig
from src.image_loader import InMemoryImage
from src.streamer import dispatch_batch, run_streamer


def test_dispatch_batch() -> None:
    pool = mock.MagicMock()
    client = mock.MagicMock()
    db = mock.MagicMock()
    img1 = InMemoryImage("1.jpg", b"d1", 1)
    img2 = InMemoryImage("2.jpg", b"d2", 2)

    dispatch_batch(pool, client, "http://mock/recognize", [img1, img2], db)
    assert pool.submit.call_count == 2


def test_run_streamer_empty_images() -> None:
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01, loop=False)
    stop_event = Event()
    mock_db = mock.MagicMock()
    with mock.patch("src.streamer.dispatch_batch") as mock_dispatch:
        run_streamer([], cfg, mock_db, stop_event)
        mock_dispatch.assert_not_called()


def test_run_streamer_single_pass() -> None:
    img1 = InMemoryImage("1.jpg", b"d1", 1)
    img2 = InMemoryImage("2.jpg", b"d2", 2)
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01, loop=False)
    stop_event = Event()
    mock_db = mock.MagicMock()
    with mock.patch("src.streamer.dispatch_batch") as mock_dispatch:
        run_streamer([img1, img2], cfg, mock_db, stop_event)
        mock_dispatch.assert_called_once()
