import io
import logging
import unittest
from unittest.mock import MagicMock, patch

import av
import requests
from PIL import Image

from src.devices import camera
from src.devices.camera import capture_all_camera_snapshots


class TestCameraDriver(unittest.TestCase):
    @patch("src.devices.camera.fetch_image_bytes")
    def test_capture_all_camera_snapshots_success(self, mock_fetch):
        def fake_fetch(url: str, timeout: float = 3.0) -> bytes | None:
            if "front" in url:
                return b"front_jpeg"
            if "rear" in url:
                return b"rear_jpeg"
            if "cabin" in url:
                return b"cabin_jpeg"
            return b"generic_jpeg"

        mock_fetch.side_effect = fake_fetch
        anpr_urls = ["http://127.0.0.1:8001/front", "http://127.0.0.1:8001/rear"]
        aux_urls = ["http://127.0.0.1:8001/cabin"]

        res = capture_all_camera_snapshots(anpr_urls, aux_urls)
        self.assertEqual(len(res), 3)
        self.assertEqual(res["anpr_1"], b"front_jpeg")
        self.assertEqual(res["anpr_2"], b"rear_jpeg")
        self.assertEqual(res["aux_1"], b"cabin_jpeg")

    def test_capture_all_camera_snapshots_empty(self):
        res = capture_all_camera_snapshots([], [])
        self.assertEqual(res, {})

    @patch("src.devices.camera.fetch_image_bytes")
    def test_capture_all_camera_snapshots_partial_failure(self, mock_fetch):
        mock_fetch.side_effect = lambda url, timeout=3.0: b"front" if "front" in url else None
        res = capture_all_camera_snapshots(["http://cam/front"], ["http://cam/aux_broken"])
        self.assertEqual(res["anpr_1"], b"front")
        self.assertIsNone(res["aux_1"])

    @patch("src.devices.camera.logger")
    def test_log_camera_fleet(self, mock_logger):
        from src.devices.camera import log_camera_fleet
        with patch("src.devices.camera.config") as mock_cfg:
            mock_cfg.anpr_camera_urls = ["http://cam/front"]
            mock_cfg.auxiliary_camera_urls = ["http://cam/top"]
            log_camera_fleet()
            self.assertTrue(any("Main / ANPR" in str(c) for c in mock_logger.info.call_args_list))
            self.assertTrue(any("Auxiliary" in str(c) for c in mock_logger.info.call_args_list))

    @patch("src.devices.camera.logger")
    def test_log_camera_fleet_empty(self, mock_logger):
        from src.devices.camera import log_camera_fleet
        with patch("src.devices.camera.config") as mock_cfg:
            mock_cfg.anpr_camera_urls = []
            mock_cfg.auxiliary_camera_urls = []
            log_camera_fleet()
            mock_logger.warning.assert_called_with("  ├── Main / ANPR Cameras: (None configured)")


def test_http_failure_log_masks_credentials(caplog):
    url = "http://admin:s3cret@10.0.0.9/snap.jpg"
    with patch("src.devices.camera.requests.get", side_effect=requests.ConnectionError(f"fail {url}")), caplog.at_level(logging.DEBUG):
        assert camera._fetch_http_snapshot(url, 1.0) is None
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text
    assert "//***@" in caplog.text


def test_http_bad_status_log_masks_credentials(caplog):
    url = "http://admin:s3cret@10.0.0.9/snap.jpg"
    with patch("src.devices.camera.requests.get", return_value=MagicMock(status_code=401, content=b"")), caplog.at_level(logging.DEBUG):
        assert camera._fetch_http_snapshot(url, 1.0) is None
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text
    assert "//***@" in caplog.text


def test_rtsp_open_failure_log_masks_credentials(caplog):
    url = "rtsp://admin:s3cret@10.0.0.9/stream"
    err = av.FFmpegError(111, "Connection refused", url)
    with patch("src.devices.camera.av.open", side_effect=err), caplog.at_level(logging.DEBUG):
        assert camera._fetch_rtsp_frame(url, 1.0) is None
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text
    assert "//***@" in caplog.text


def test_rtsp_read_failure_log_masks_credentials(caplog):
    url = "rtsp://admin:s3cret@10.0.0.9/stream"
    container = MagicMock()
    container.__enter__.return_value.decode.return_value = iter(())
    with patch("src.devices.camera.av.open", return_value=container), caplog.at_level(logging.DEBUG):
        assert camera._fetch_rtsp_frame(url, 1.0) is None
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text
    assert "//***@" in caplog.text


def test_rtsp_exception_log_masks_credentials(caplog):
    url = "rtsp://admin:s3cret@10.0.0.9/stream"
    with patch("src.devices.camera.av.open", side_effect=OSError(f"boom {url}")), caplog.at_level(logging.DEBUG):
        assert camera._fetch_rtsp_frame(url, 1.0) is None
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text


def test_rtsp_no_video_stream_returns_none(caplog):
    url = "rtsp://admin:s3cret@10.0.0.9/audio_only"
    container = MagicMock()
    container.__enter__.return_value.decode.side_effect = IndexError("no video stream")
    with patch("src.devices.camera.av.open", return_value=container), caplog.at_level(logging.DEBUG):
        assert camera._fetch_rtsp_frame(url, 1.0) is None
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text
    assert "//***@" in caplog.text


def test_rtsp_grab_decodes_real_stream_to_jpeg(tmp_path):
    clip = tmp_path / "clip.mp4"  # local file stands in for rtsp://; same av.open/decode path
    with av.open(str(clip), "w") as out:
        stream = out.add_stream("mpeg4", rate=10)
        stream.width, stream.height, stream.pix_fmt = 320, 240, "yuv420p"
        for i in range(3):
            frame = av.VideoFrame.from_image(Image.new("RGB", (320, 240), (i * 60, 90, 180)))
            for pkt in stream.encode(frame):
                out.mux(pkt)
        for pkt in stream.encode():
            out.mux(pkt)
    jpeg = camera._fetch_rtsp_frame(str(clip), 3.0)
    assert jpeg is not None and jpeg[:2] == b"\xff\xd8"
    assert Image.open(io.BytesIO(jpeg)).size == (320, 240)


def test_log_camera_fleet_masks_credentials(caplog):
    with patch("src.devices.camera.config") as cfg:
        cfg.anpr_camera_urls = ["rtsp://admin:s3cret@10.0.0.9/stream"]
        cfg.auxiliary_camera_urls = ["http://admin:s3cret@10.0.0.10/snap.jpg"]
        with caplog.at_level(logging.DEBUG):
            camera.log_camera_fleet()
    assert "s3cret" not in caplog.text and "admin:" not in caplog.text
    assert "//***@10.0.0.9/stream" in caplog.text


if __name__ == "__main__":
    unittest.main()
