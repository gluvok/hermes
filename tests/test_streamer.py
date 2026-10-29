"""Unit tests for vehicle image streamer scheduling and task lifecycle."""
import asyncio
from unittest import mock

from src.config import StreamerConfig
from src.image_loader import InMemoryImage
from src.streamer import run_streamer


def test_run_streamer_empty_images() -> None:
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01)
    with mock.patch("src.streamer.send_image") as mock_send:
        results = asyncio.run(run_streamer([], cfg))
        mock_send.assert_not_called()
        assert results == []


def test_run_streamer_single_pass() -> None:
    img1 = InMemoryImage("1.jpg", b"d1", 1)
    img2 = InMemoryImage("2.jpg", b"d2", 2)
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01)
    with mock.patch(
        "src.streamer.send_image",
        side_effect=[{"results": [{"plate": "P1"}]}, None],
    ) as mock_send:
        results = asyncio.run(run_streamer([img1, img2], cfg))
        assert mock_send.call_count == 2
        assert results == [{"results": [{"plate": "P1"}]}, None]
