from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from src.config import ConfigManager
from src.config.constants import CLOUD_POST_MAX_ATTEMPTS
from src.integrations import gluvok


@pytest.fixture(autouse=True)
def _credentials_and_no_sleep():
    with (
        patch.object(ConfigManager, "device_id", "test-device"),
        patch.object(ConfigManager, "device_key", "test-device-key"),
        patch.object(gluvok._post_entry.retry, "sleep", lambda _s: None),
    ):
        yield


def _resp(code: int, text: str = "err") -> Mock:
    return Mock(status_code=code, content=b'{"id": 7}', text=text, json=lambda: {"id": 7})


def _send(mock_post: Mock, *outcomes, **kwargs):
    mock_post.side_effect = list(outcomes)
    return gluvok.transmit_entry_multipart(1, "MH12AB1234", 10.0, **kwargs)


@patch("src.integrations.gluvok.requests.post")
def test_retries_transient_failures_with_same_idempotency_key(mock_post):
    ok, entry_id, _, _ = _send(
        mock_post, _resp(503), requests.ConnectionError("down"), _resp(201), idempotency_key="k-1"
    )
    assert ok and entry_id == "7" and mock_post.call_count == 3
    assert {c.kwargs["headers"]["Idempotency-Key"] for c in mock_post.call_args_list} == {"k-1"}


@pytest.mark.parametrize("code", [408, 429])
@patch("src.integrations.gluvok.requests.post")
def test_retries_request_timeout_and_rate_limit(mock_post, code):
    ok, _, _, _ = _send(mock_post, _resp(code), _resp(201))
    assert ok and mock_post.call_count == 2


@pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
@patch("src.integrations.gluvok.requests.post")
def test_does_not_retry_client_errors(mock_post, code):
    ok, _, err, _ = _send(mock_post, _resp(code))
    assert not ok and err.startswith(f"HTTP {code}") and mock_post.call_count == 1


@patch("src.integrations.gluvok.requests.post")
def test_gives_up_after_max_attempts_with_last_response(mock_post):
    ok, _, err, _ = _send(mock_post, *[_resp(500)] * CLOUD_POST_MAX_ATTEMPTS)
    assert not ok and err.startswith("HTTP 500") and mock_post.call_count == CLOUD_POST_MAX_ATTEMPTS


@patch("src.integrations.gluvok.requests.post")
def test_gives_up_after_max_attempts_with_last_exception(mock_post):
    ok, _, err, timed_out = _send(mock_post, *[requests.ConnectionError("down")] * CLOUD_POST_MAX_ATTEMPTS)
    assert not ok and err.startswith("ConnectionError") and not timed_out
    assert mock_post.call_count == CLOUD_POST_MAX_ATTEMPTS


@patch("src.integrations.gluvok.requests.post")
def test_read_timeout_is_retried_then_reported_as_timed_out(mock_post):
    ok, _, err, timed_out = _send(mock_post, *[requests.ReadTimeout("slow")] * CLOUD_POST_MAX_ATTEMPTS)
    assert not ok and err.startswith("ReadTimeout") and timed_out
    assert mock_post.call_count == CLOUD_POST_MAX_ATTEMPTS


@patch("src.integrations.gluvok.requests.post")
def test_generates_idempotency_key_when_not_given(mock_post):
    _send(mock_post, _resp(201))
    assert mock_post.call_args.kwargs["headers"]["Idempotency-Key"]


@patch("src.integrations.gluvok.requests.post")
def test_storage_fallback_post_reuses_idempotency_key(mock_post):
    ok, _, _, _ = _send(
        mock_post,
        _resp(400, "Storage upload failed"),
        _resp(201),
        images=[("a.jpg", b"img")],
        idempotency_key="k-2",
    )
    assert ok and mock_post.call_count == 2
    assert {c.kwargs["headers"]["Idempotency-Key"] for c in mock_post.call_args_list} == {"k-2"}


def test_snapshot_images_sorts_cameras_and_skips_empty():
    payload = {"camera_snapshots": {"b": b"2", "a": b"1", "c": b"", "d": None}}
    assert gluvok.snapshot_images(payload) == [("truck_a.jpg", b"1"), ("truck_b.jpg", b"2")]
    assert gluvok.snapshot_images({}) == []
