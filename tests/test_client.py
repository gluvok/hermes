"""Unit tests for recognition HTTP client and plate extraction."""
import asyncio
from unittest import mock

from src.client import extract_first_plate, send_image
from src.image_loader import InMemoryImage


def test_extract_first_plate() -> None:
    multi = {"results": [{"plate": "FIRST"}, {"plate": "SECOND"}]}
    assert extract_first_plate(multi) == "FIRST"
    assert extract_first_plate({"results": []}) is None
    assert extract_first_plate({}) is None


def test_send_image_success() -> None:
    img = InMemoryImage("1.jpg", b"bytes", 1)
    mock_client = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.json.return_value = {"results": [{"plate": "DL10CE0589"}]}
    mock_client.post = mock.AsyncMock(return_value=mock_resp)
    sem = asyncio.Semaphore(2)

    result = asyncio.run(
        send_image(mock_client, "http://mock/recognize", img, sem)
    )
    assert result == {"results": [{"plate": "DL10CE0589"}]}
    mock_client.post.assert_awaited_once()


def test_send_image_failure() -> None:
    img = InMemoryImage("fail.jpg", b"bytes", 2)
    mock_client = mock.MagicMock()
    mock_client.post = mock.AsyncMock(side_effect=OSError("Connection refused"))
    sem = asyncio.Semaphore(2)

    result = asyncio.run(
        send_image(mock_client, "http://mock/recognize", img, sem)
    )
    assert result is None
    mock_client.post.assert_awaited_once()
