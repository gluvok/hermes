import unittest

from src.config import config
from src.web.app import create_app
from src.web.auth import create_session_token


class TestCropApi(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.token = create_session_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def test_get_config_includes_crop_padding(self):
        res = self.client.get("/api/config", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("crop_pad_top", data)
        self.assertIn("crop_pad_bottom", data)
        self.assertIn("crop_pad_left", data)
        self.assertIn("crop_pad_right", data)

    def test_post_config_updates_crop_padding(self):
        payload = {
            "crop_pad_top": 12.0,
            "crop_pad_bottom": 14.5,
            "crop_pad_left": 18.0,
            "crop_pad_right": 20.0,
        }
        res = self.client.post("/api/config", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        self.assertEqual(config.crop_pad_top, 12.0)
        self.assertEqual(config.crop_pad_bottom, 14.5)
        self.assertEqual(config.crop_pad_left, 18.0)
        self.assertEqual(config.crop_pad_right, 20.0)

    def test_post_config_rejects_out_of_range_padding(self):
        payload = {
            "crop_pad_top": 150.0,  # Invalid: > 100%
        }
        res = self.client.post("/api/config", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("between 0.0 and 100.0 percent", data.get("error", ""))
