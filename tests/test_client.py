"""Unit tests for recognition HTTP client and plate extraction."""
from unittest import mock

from src.client import extract_first_plate, send_and_record_image
from src.image_loader import InMemoryImage


def test_extract_first_plate() -> None:
    multi = {"results": [{"plate": "FIRST"}, {"plate": "SECOND"}]}
    assert extract_first_plate(multi) == "FIRST"
    assert extract_first_plate({"results": []}) is None
    assert extract_first_plate({}) is None


def test_send_and_record_image_success() -> None:
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


def test_send_and_record_image_failure() -> None:
    img = InMemoryImage("fail.jpg", b"bytes", 2)
    mock_client = mock.MagicMock()
    mock_client.post.side_effect = OSError("Connection refused")
    mock_db = mock.MagicMock()

    result = send_and_record_image(
        mock_client, "http://mock/recognize", img, mock_db
    )
    assert result is None
    mock_db.save_detection.assert_not_called()
