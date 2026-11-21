from __future__ import annotations

import json
import unittest

from src.web import auth
from src.web.app import create_app
from src.web.auth import reset_auth_state


class TestLogout(unittest.TestCase):
    def setUp(self):
        reset_auth_state()
        self.client = create_app({"TESTING": True}).test_client()

    def _login(self) -> str:
        res = self.client.post(
            "/api/login",
            data=json.dumps({"userid": "superadmin", "password": auth.SUPERADMIN_PASS}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        return res.get_json()["token"]

    @staticmethod
    def _bearer(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_token_rejected_after_logout(self):
        token = self._login()
        self.assertEqual(self.client.get("/api/config", headers=self._bearer(token)).status_code, 200)

        res = self.client.post("/api/logout", headers=self._bearer(token))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.get("/api/config", headers=self._bearer(token)).status_code, 401)

    def test_logout_revokes_only_presented_token(self):
        first, second = self._login(), self._login()

        self.client.post("/api/logout", headers=self._bearer(first))

        self.assertEqual(self.client.get("/api/config", headers=self._bearer(first)).status_code, 401)
        self.assertEqual(self.client.get("/api/config", headers=self._bearer(second)).status_code, 200)

    def test_logout_without_or_with_invalid_token_is_ok(self):
        survivor = self._login()

        self.assertEqual(self.client.post("/api/logout").status_code, 200)
        self.assertEqual(
            self.client.post("/api/logout", headers=self._bearer("not-a-real-token")).status_code, 200
        )
        self.assertEqual(self.client.get("/api/config", headers=self._bearer(survivor)).status_code, 200)

    def test_logout_accepts_x_auth_token_header(self):
        token = self._login()

        self.client.post("/api/logout", headers={"X-Auth-Token": token})

        self.assertEqual(self.client.get("/api/config", headers=self._bearer(token)).status_code, 401)

    def test_index_logout_calls_server(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("/api/logout", html)
