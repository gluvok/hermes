import unittest
from unittest.mock import patch, MagicMock
from src.integrations.anpr import send_frame_to_anpr_server

class TestArgusContract(unittest.TestCase):
    def setUp(self):
        # Minimal valid JPEG magic header + dummy payload
        self.dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 128 + b"\xff\xd9"

    def test_query_anpr_matches_argus_response_schema(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"results": [{"plate": "HR26DK8333", "confidence": 0.942, "tier": "tier1_fast_alpr"}], "execution_time_ms": 45.2}'
        mock_response.json.return_value = {
            "results": [
                {
                    "plate": "HR26DK8333",
                    "confidence": 0.942,
                    "tier": "tier1_fast_alpr"
                }
            ],
            "execution_time_ms": 45.2
        }
        with patch("requests.post", return_value=mock_response):
            plate, status = send_frame_to_anpr_server(self.dummy_jpeg, "http://127.0.0.1:8000/recognize")
            self.assertEqual(plate, "HR26DK8333")
            self.assertEqual(status, "SUCCESS")

    def test_query_anpr_handles_no_plate_fallback(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"results": [], "execution_time_ms": 22.1}'
        mock_response.json.return_value = {
            "results": [],
            "execution_time_ms": 22.1
        }
        with patch("requests.post", return_value=mock_response):
            plate, status = send_frame_to_anpr_server(self.dummy_jpeg, "http://127.0.0.1:8000/recognize")
            self.assertIsNone(plate)
            self.assertEqual(status, "NO_PLATE_DETECTED")
