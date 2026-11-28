import concurrent.futures
import unittest
from unittest.mock import MagicMock, patch

import requests

from src.integrations.anpr import (
    _parse_vehicle_box,
    dispatch_anpr_batch,
    get_highest_frequency_plate,
    send_and_record_anpr_frame,
    send_frame_to_anpr_server,
)


class TestANPRClient(unittest.TestCase):
    def test_send_frame_empty_bytes(self):
        plate, status = send_frame_to_anpr_server(b"")
        self.assertIsNone(plate)
        self.assertEqual(status, "EMPTY_IMAGE")

        plate_none, status_none = send_frame_to_anpr_server(None)
        self.assertIsNone(plate_none)
        self.assertEqual(status_none, "EMPTY_IMAGE")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_argus_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "frame.jpg",
            "humans_outside": 0,
            "humans_inside": 0,
            "results": [
                {
                    "plate": "RJ09GA0165",
                    "vehicle_type": "car",
                    "state": "Rajasthan",
                    "raw_text": "RJ09GA0165",
                    "confidence": 0.98,
                }
            ],
            "execution_time_ms": 115.4,
        }
        mock_post.return_value = mock_response

        fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        plate, status = send_frame_to_anpr_server(fake_img, server_url="http://127.0.0.1:8000/recognize")

        self.assertEqual(plate, "RJ09GA0165")
        self.assertEqual(status, "SUCCESS")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://127.0.0.1:8000/recognize")
        self.assertIn("file", kwargs["files"])

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_argus_empty_results(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "frame.jpg",
            "humans_outside": 0,
            "humans_inside": 0,
            "results": [],
            "execution_time_ms": 42.1,
        }
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertIsNone(plate)
        self.assertEqual(status, "NO_PLATE_DETECTED")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_fallback_flat_json(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "plate": "MH12AB1234",
            "confidence": 0.95,
        }
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertEqual(plate, "MH12AB1234")
        self.assertEqual(status, "SUCCESS")

    @patch("src.integrations.anpr.requests.post")
    def test_argus_response_is_logged(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"results": [{"plate": "KA01AB9999"}]}'
        mock_response.json.return_value = {"results": [{"plate": "KA01AB9999"}]}
        mock_post.return_value = mock_response

        with self.assertLogs("src.integrations.anpr", level="INFO") as cm:
            plate, _ = send_frame_to_anpr_server(b"fake-bytes")
            self.assertEqual(plate, "KA01AB9999")
            self.assertTrue(any("[ANPR] [Argus Response] Status 200" in msg for msg in cm.output))

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Read timeout")
        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertIsNone(plate)
        self.assertEqual(status, "ANPR_TIMEOUT")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_connection_error(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertIsNone(plate)
        self.assertEqual(status, "ANPR_CONNECTION_ERROR")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_argus_multi_vehicle_picks_first(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "4.jpg",
            "humans_outside": 0,
            "humans_inside": 0,
            "results": [
                {
                    "plate": "RJ43GA2012",
                    "vehicle_type": "truck",
                    "state": "Rajasthan",
                    "raw_text": "m RJ43GA2012 SUPER FAST",
                    "confidence": 0.9993,
                    "box": [512, 387, 575, 409],
                },
                {
                    "plate": "RJ43GA2012",
                    "vehicle_type": "truck",
                    "state": "Rajasthan",
                    "raw_text": "TATA RJ436A.2012",
                    "confidence": 0.8568,
                    "box": [131, 400, 207, 423],
                },
            ],
            "execution_time_ms": 1915.68,
        }
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertEqual(plate, "RJ43GA2012")
        self.assertEqual(status, "SUCCESS")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_argus_multi_vehicle_different_plates_takes_first(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "multi.jpg",
            "humans_outside": 0,
            "humans_inside": 0,
            "results": [
                {
                    "plate": "RJ43GA2012",
                    "vehicle_type": "truck",
                    "confidence": 0.99,
                },
                {
                    "plate": "DL01AB9999",
                    "vehicle_type": "car",
                    "confidence": 0.95,
                },
            ],
            "execution_time_ms": 1500.0,
        }
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        # results array is already sorted by Argus; results[0] is authoritative
        self.assertEqual(plate, "RJ43GA2012")
        self.assertEqual(status, "SUCCESS")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_argus_first_plate_none_yields_no_plate(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "multi_unreadable.jpg",
            "results": [
                {
                    "plate": None,
                    "vehicle_type": "truck",
                    "confidence": 0.30,
                },
                {
                    "plate": "DL01AB9999",
                    "vehicle_type": "car",
                    "confidence": 0.95,
                },
            ],
            "execution_time_ms": 1200.0,
        }
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        # Since results[0] is best candidate and has no plate, return NO_PLATE_DETECTED
        self.assertIsNone(plate)
        self.assertEqual(status, "NO_PLATE_DETECTED")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_argus_all_empty_plates(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "filename": "multi_unreadable.jpg",
            "results": [
                {"plate": None, "vehicle_type": "truck"},
                {"plate": "", "vehicle_type": "car"},
                {"plate": "N/A", "vehicle_type": "bike"},
            ],
            "execution_time_ms": 1200.0,
        }
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertIsNone(plate)
        self.assertEqual(status, "NO_PLATE_DETECTED")

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_non_json_200_returns_bad_response(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>502 Bad Gateway from reverse proxy</body></html>"
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_post.return_value = mock_response

        plate, status = send_frame_to_anpr_server(b"fake-bytes")
        self.assertIsNone(plate)
        self.assertEqual(status, "ANPR_BAD_RESPONSE")

    def test_highest_frequency_voting(self):
        samples = ["MH12AB1234", "MH12AB1234", "MH12AB1234", "MH12AB1235", "DL01AB9999"]
        winner = get_highest_frequency_plate(samples)
        self.assertEqual(winner, "MH12AB1234")

    def test_highest_frequency_empty_list(self):
        winner = get_highest_frequency_plate([])
        self.assertEqual(winner, "NO_PLATE_DETECTED")

        winner_none = get_highest_frequency_plate([None, "", "   "])
        self.assertEqual(winner_none, "NO_PLATE_DETECTED")

    def test_parse_vehicle_box_valid(self):
        self.assertEqual(_parse_vehicle_box([10, 10, 50, 50]), (10, 10, 50, 50))
        self.assertEqual(_parse_vehicle_box((10.4, 10.6, 50.2, 50.8)), (10, 11, 50, 51))

    def test_parse_vehicle_box_missing_and_invalid(self):
        invalid_cases = [
            None,
            [],
            [10, 10, 50],
            [10, 10, 50, 50, 60],
            "10,10,50,50",
            {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
            [True, 10, 50, 50],
            [10, 10, "50", 50],
            [float("nan"), 10, 50, 50],
            [10, float("inf"), 50, 50],
            [10, 10, float("-inf"), 50],
            [50, 10, 50, 50],
            [60, 10, 50, 50],
            [10, 50, 50, 50],
            [10, 60, 50, 50],
            [10.1, 10, 10.2, 50],
        ]
        for raw in invalid_cases:
            with self.subTest(raw=raw):
                self.assertIsNone(_parse_vehicle_box(raw))

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_meta_out_argus_vehicle_box(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "plate": "RJ09GA0165",
                    "vehicle_box": [10, 10, 50, 50],
                    "execution_time_ms": 31.42,
                }
            ],
            "execution_time_ms": 31.42,
        }
        mock_post.return_value = mock_response

        meta: dict[str, object] = {}
        plate, status = send_frame_to_anpr_server(b"fake-bytes", meta_out=meta)
        self.assertEqual(plate, "RJ09GA0165")
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(meta["vehicle_box"], (10, 10, 50, 50))

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_meta_out_no_plate_still_extracts_vehicle_box(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "plate": None,
                    "vehicle_box": [12.4, 20.6, 100.1, 200.9],
                }
            ]
        }
        mock_post.return_value = mock_response

        meta: dict[str, object] = {}
        plate, status = send_frame_to_anpr_server(b"fake-bytes", meta_out=meta)
        self.assertIsNone(plate)
        self.assertEqual(status, "NO_PLATE_DETECTED")
        self.assertEqual(meta["vehicle_box"], (12, 21, 100, 201))

    @patch("src.integrations.anpr.requests.post")
    def test_send_frame_meta_out_flat_json_and_missing_or_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "plate": "MH12AB1234",
            "vehicle_box": [5, 6, 70, 80],
        }
        mock_post.return_value = mock_response

        meta_flat: dict[str, object] = {}
        plate, status = send_frame_to_anpr_server(b"fake-bytes", meta_out=meta_flat)
        self.assertEqual(plate, "MH12AB1234")
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(meta_flat["vehicle_box"], (5, 6, 70, 80))

        meta_empty: dict[str, object] = {"vehicle_box": (1, 2, 3, 4)}
        plate_empty, status_empty = send_frame_to_anpr_server(b"", meta_out=meta_empty)
        self.assertIsNone(plate_empty)
        self.assertEqual(status_empty, "EMPTY_IMAGE")
        self.assertIsNone(meta_empty["vehicle_box"])

    @patch("src.integrations.anpr.requests.post")
    def test_send_and_record_anpr_frame_with_box_callback(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"plate": "RJ09GA0165", "vehicle_box": [10, 10, 50, 50]}]
        }
        mock_post.return_value = mock_response

        legacy_calls: list[tuple] = []
        box_calls: list[tuple] = []
        img = b"raw-jpeg-bytes"

        plate, status = send_and_record_anpr_frame(
            session_id="SESS_1",
            cam_idx=2,
            image_bytes=img,
            callback=lambda sid, cam, p, st: legacy_calls.append((sid, cam, p, st)),
            box_callback=lambda sid, cam, p, st, box, raw: box_calls.append(
                (sid, cam, p, st, box, raw)
            ),
        )

        self.assertEqual(plate, "RJ09GA0165")
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(legacy_calls, [("SESS_1", 2, "RJ09GA0165", "SUCCESS")])
        self.assertEqual(
            box_calls, [("SESS_1", 2, "RJ09GA0165", "SUCCESS", (10, 10, 50, 50), img)]
        )

    @patch("src.integrations.anpr.requests.post")
    def test_dispatch_anpr_batch_invokes_box_callback(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"plate": "DL01AA1111", "vehicle_box": [20, 30, 120, 130]}]
        }
        mock_post.return_value = mock_response

        box_calls: list[tuple] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = dispatch_anpr_batch(
                pool=pool,
                session_id="SESS_BATCH",
                batch=[(1, b"frame-1"), (2, b"frame-2")],
                box_callback=lambda sid, cam, p, st, box, raw: box_calls.append(
                    (sid, cam, p, st, box, raw)
                ),
            )
            concurrent.futures.wait(futures, timeout=2.0)

        self.assertEqual(len(box_calls), 2)
        by_cam = {call[1]: call for call in box_calls}
        self.assertEqual(
            by_cam[1],
            ("SESS_BATCH", 1, "DL01AA1111", "SUCCESS", (20, 30, 120, 130), b"frame-1"),
        )
        self.assertEqual(
            by_cam[2],
            ("SESS_BATCH", 2, "DL01AA1111", "SUCCESS", (20, 30, 120, 130), b"frame-2"),
        )


if __name__ == "__main__":
    unittest.main()
