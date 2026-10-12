"""Unit tests for vehicle image streamer and plate extraction."""
from pathlib import Path
from threading import Event
from unittest import mock

from src.client import extract_first_plate, send_and_record_image
from src.config import StreamerConfig
from src.image_loader import InMemoryImage, load_images_to_memory
from src.streamer import run_streamer


def test_natural_sorting_and_ram_load(tmp_path: Path) -> None:
    for name in ["10.jpg", "1.jpg", "2.jpg"]:
        (tmp_path / name).write_bytes(b"image_content")
    images = load_images_to_memory(tmp_path)
    assert [img.name for img in images] == ["1.jpg", "2.jpg", "10.jpg"]
    assert images[0].data == b"image_content"


def test_extract_first_plate() -> None:
    multi = {"results": [{"plate": "FIRST"}, {"plate": "SECOND"}]}
    assert extract_first_plate(multi) == "FIRST"
    assert extract_first_plate({"results": []}) is None
    assert extract_first_plate({}) is None


def test_send_and_record_image() -> None:
    img = InMemoryImage("1.jpg", b"bytes", 1)
    mock_client = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {"results": [{"plate": "DL10CE0589"}]}
    mock_client.post.return_value = mock_resp
    mock_db = mock.MagicMock()

    result = send_and_record_image(
        mock_client, "http://mock/recognize", img, mock_db
    )
    assert result == {"results": [{"plate": "DL10CE0589"}]}
    mock_db.save_detection.assert_called_once_with(
        "1.jpg", "DL10CE0589", b"bytes"
    )


def test_run_streamer_single_pass() -> None:
    img1 = InMemoryImage("1.jpg", b"d1", 1)
    img2 = InMemoryImage("2.jpg", b"d2", 2)
    cfg = StreamerConfig(batch_size=2, interval_sec=0.01, loop=False)
    stop_event = Event()
    mock_db = mock.MagicMock()
    with mock.patch("src.streamer.send_and_record_image") as mock_send:
        run_streamer([img1, img2], cfg, mock_db, stop_event)
        assert mock_send.call_count == 2
