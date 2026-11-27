from __future__ import annotations

import io
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch

import requests
from PIL import Image

from src.config import ConfigManager, config
from src.core.telemetry import get_error_counts, get_system_events, reset_state
from src.integrations.gluvok import (
    _build_multipart_files,
    post_to_cloud,
    transmit_entry_multipart,
)


class TestCloudPost(unittest.TestCase):
    def setUp(self):
        reset_state()
        for name, value in (("device_id", "test-device"), ("device_key", "test-device-key")):
            patcher = patch.object(ConfigManager, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        reset_state()

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_success_201_preserves_payload(self, mock_post: Mock):
        mock_resp = Mock(status_code=201, content=b'{"data": {"id": 99}}')
        mock_resp.json.return_value = {"data": {"id": 99}}
        mock_post.return_value = mock_resp

        session = {
            "weight": 35200.0,
            "anpr_plate": "DL1CAB1234",
            "camera_snapshots": {"anpr_1": b"truck_img"},
        }
        post_to_cloud(session)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs

        # 1. Verify x-api-key header carries the device key; no Basic auth (janus ingest)
        self.assertEqual(call_kwargs["headers"], {"x-api-key": str(config.device_key)})
        self.assertNotIn("auth", call_kwargs)

        # 2. Verify form data
        data = call_kwargs["data"]
        self.assertEqual(data["detected_vehicle_number"], "DL1CAB1234")
        self.assertEqual(data["weight"], "35200.0")
        self.assertEqual(data["center_id"], str(config.center_id))

        # 3. Verify multipart file attachment
        files = call_kwargs["files"]
        self.assertIsNotNone(files)
        self.assertEqual(files[0][0], "file")
        self.assertEqual(files[0][1][1], b"truck_img")

        # 4. Verify session payload is NOT cleared
        self.assertGreater(len(session), 0)

        events = get_system_events()
        self.assertTrue(any("Entry #99 created" in ev["message"] for ev in events))

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_aborts_when_credentials_missing(self, mock_post: Mock):
        with patch.object(ConfigManager, "device_key", ""):
            session = {"weight": 1000.0, "anpr_plate": "MH12AB1234"}
            post_to_cloud(session)

        mock_post.assert_not_called()
        error_counts = get_error_counts()
        self.assertGreaterEqual(error_counts.get("CLOUD_AUTH_FAILED", 0), 1)

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_401_unauthorized(self, mock_post: Mock):
        mock_resp = Mock(status_code=401, content=b"Unauthorized", text="Unauthorized")
        mock_post.return_value = mock_resp

        session = {"weight": 1000.0, "anpr_plate": "MH12AB1234"}
        post_to_cloud(session)

        error_counts = get_error_counts()
        self.assertGreaterEqual(error_counts.get("CLOUD_AUTH_FAILED", 0), 1)

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_403_forbidden(self, mock_post: Mock):
        mock_resp = Mock(status_code=403, content=b"Forbidden", text="Device deactivated")
        mock_post.return_value = mock_resp

        session = {"weight": 1000.0, "anpr_plate": "MH12AB1234"}
        post_to_cloud(session)

        error_counts = get_error_counts()
        self.assertGreaterEqual(error_counts.get("CLOUD_AUTH_FORBIDDEN", 0), 1)

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_400_bad_request(self, mock_post: Mock):
        mock_resp = Mock(status_code=400, content=b"Bad Request", text="Invalid weight")
        mock_post.return_value = mock_resp

        session = {"weight": -10.0, "anpr_plate": "MH12AB1234"}
        post_to_cloud(session)

        error_counts = get_error_counts()
        self.assertGreaterEqual(error_counts.get("CLOUD_VALIDATION_ERROR", 0), 1)

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_500_server_error(self, mock_post: Mock):
        mock_resp = Mock(status_code=500, content=b"Server Error", text="Internal Error")
        mock_post.return_value = mock_resp

        session = {"weight": 5000.0, "anpr_plate": "MH12AB1234"}
        post_to_cloud(session)

        error_counts = get_error_counts()
        self.assertGreaterEqual(error_counts.get("CLOUD_UPLOAD_ERROR", 0), 1)

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_network_exception(self, mock_post: Mock):
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        session = {"weight": 5000.0, "anpr_plate": "MH12AB1234"}
        post_to_cloud(session)

        error_counts = get_error_counts()
        self.assertGreaterEqual(error_counts.get("CLOUD_UPLOAD_ERROR", 0), 1)

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_with_camera_snapshots(self, mock_post: Mock):
        mock_resp = Mock(status_code=201, content=b'{"data": {"id": 105}}')
        mock_resp.json.return_value = {"data": {"id": 105}}
        mock_post.return_value = mock_resp

        session = {
            "weight": 44100.0,
            "anpr_plate": "HR26DK8333",
            "camera_snapshots": {
                "anpr_1": b"front_img",
                "anpr_2": b"rear_img",
                "aux_1": b"cabin_img",
            },
        }
        post_to_cloud(session)

        mock_post.assert_called_once()
        files = mock_post.call_args.kwargs["files"]
        self.assertEqual(len(files), 3)
        filenames = [f[1][0] for f in files]
        self.assertEqual(filenames, ["truck_anpr_1.jpg", "truck_anpr_2.jpg", "truck_aux_1.jpg"])

    @patch("src.integrations.gluvok.requests.post")
    def test_post_to_cloud_storage_retry_uses_api_key_header(self, mock_post: Mock):
        storage_err = Mock(status_code=400, content=b"storage error", text="storage error")
        ok_resp = Mock(status_code=201, content=b'{"data": {"id": 106}}')
        ok_resp.json.return_value = {"data": {"id": 106}}
        mock_post.side_effect = [storage_err, ok_resp]

        post_to_cloud({
            "weight": 25000.0,
            "anpr_plate": "MH12AB1234",
            "camera_snapshots": {"anpr_1": b"truck_img"},
        })

        self.assertEqual(mock_post.call_count, 2)
        for call in mock_post.call_args_list:
            self.assertEqual(call.kwargs["headers"], {"x-api-key": str(config.device_key)})
            self.assertNotIn("auth", call.kwargs)

    def test_transmit_does_not_forward_api_key_on_redirect(self):
        seen: list[str | None] = []

        def serve(handler_fn):
            class Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    self.rfile.read(int(self.headers.get("Content-Length", 0)))
                    handler_fn(self)

                def log_message(self, format, *args):
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)
            return server.server_address[1]

        def record_and_ok(h):
            seen.append(h.headers.get("x-api-key"))
            h.send_response(201)
            h.send_header("Content-Length", "0")
            h.end_headers()

        port_b = serve(record_and_ok)

        def redirect(h):
            h.send_response(307)
            h.send_header("Location", f"http://localhost:{port_b}/steal")
            h.send_header("Content-Length", "0")
            h.end_headers()

        port_a = serve(redirect)

        with patch("src.integrations.gluvok.GLUVOK_BASE_URL", f"http://127.0.0.1:{port_a}"):
            result = transmit_entry_multipart(1, "MH12AB1234", 100.0)

        self.assertEqual(seen, [])
        self.assertFalse(result[0])

    def test_build_multipart_files_passes_bytes_through_untouched(self):
        # Snapshots are already compressed in session.py; re-encoding is lossy and wastes Pi CPU.
        buf = io.BytesIO()
        Image.effect_noise((64, 64), 64).convert("RGB").save(buf, "JPEG", quality=95)
        jpeg = buf.getvalue()

        files, has_images = _build_multipart_files([("a.jpg", jpeg)], None, "f.jpg")
        self.assertTrue(has_images)
        self.assertEqual(files, [("file", ("a.jpg", jpeg, "image/jpeg"))])

        files, has_images = _build_multipart_files(None, jpeg, "f.jpg")
        self.assertTrue(has_images)
        self.assertEqual(files, [("file", ("f.jpg", jpeg, "image/jpeg"))])


if __name__ == "__main__":
    unittest.main()
