from src.web import auth
from src.web.app import create_app


def _login(c, ip, pw):
    return c.post("/api/login", json={"userid": "superadmin", "password": pw},
                  environ_base={"REMOTE_ADDR": ip})


def test_failures_from_one_ip_do_not_block_another(monkeypatch):
    monkeypatch.setattr("src.web.blueprints.api.time.sleep", lambda s: None)
    auth.reset_auth_state()
    c = create_app({"TESTING": True}).test_client()
    for _ in range(5):
        assert _login(c, "10.0.0.66", "wrong").status_code == 401
    assert _login(c, "10.0.0.66", "wrong").status_code == 429
    assert _login(c, "10.0.0.5", auth.SUPERADMIN_PASS).status_code == 200


def test_submitted_userid_never_reaches_status(monkeypatch):
    monkeypatch.setattr("src.web.blueprints.api.time.sleep", lambda s: None)
    auth.reset_auth_state()
    c = create_app({"TESTING": True}).test_client()
    c.post("/api/login", json={"userid": "<b>x</b>", "password": "nope"})
    assert "<b>x</b>" not in c.get("/api/status").get_data(as_text=True)


def test_failed_login_event_logs_client_ip(monkeypatch):
    monkeypatch.setattr("src.web.blueprints.api.time.sleep", lambda s: None)
    auth.reset_auth_state()
    c = create_app({"TESTING": True}).test_client()
    _login(c, "10.0.0.66", "wrong")
    token = _login(c, "10.0.0.5", auth.SUPERADMIN_PASS).get_json()["token"]
    status = c.get("/api/status", headers={"X-Auth-Token": token})
    assert "10.0.0.66" in status.get_data(as_text=True)
