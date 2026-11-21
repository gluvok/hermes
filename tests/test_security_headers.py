from __future__ import annotations

from src.web.app import create_app


def test_status_has_no_cors_headers():
    response = create_app({"TESTING": True}).test_client().get("/api/status")

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Headers" not in response.headers
    assert "Access-Control-Allow-Methods" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_csp_header_on_page_and_api():
    client = create_app({"TESTING": True}).test_client()

    for path in ("/", "/api/status"):
        csp = client.get(path).headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
