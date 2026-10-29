"""Unit tests for vehicle image streamer scheduling and task lifecycle."""
import asyncio
from unittest import mock

from src.config import StreamerConfig
from src.image_loader import InMemoryImage
from src.streamer import cancel_active_tasks, run_streamer


def test_cancel_active_tasks() -> None:
    t_done = mock.MagicMock(done=mock.MagicMock(return_value=True))
    t_pending = mock.MagicMock(done=mock.MagicMock(return_value=False))
    cancel_active_tasks({t_done, t_pending})
    t_done.cancel.assert_not_called()
    t_pending.cancel.assert_called_once()


def test_run_streamer_empty_images() -> None:
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01, loop=False)
    stop_event = asyncio.Event()
    with mock.patch("src.streamer.send_image") as mock_send:
        asyncio.run(run_streamer([], cfg, stop_event))
        mock_send.assert_not_called()


def test_run_streamer_single_pass() -> None:
    img1 = InMemoryImage("1.jpg", b"d1", 1)
    img2 = InMemoryImage("2.jpg", b"d2", 2)
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01, loop=False)
    stop_event = asyncio.Event()
    with mock.patch("src.streamer.send_image") as mock_send:
        asyncio.run(run_streamer([img1, img2], cfg, stop_event))
        assert mock_send.call_count == 2
