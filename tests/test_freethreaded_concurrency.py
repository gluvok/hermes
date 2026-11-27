"""test_freethreaded_concurrency.py — Races that only bite once threads truly run in parallel (3.14t)."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from src.integrations.anpr import dispatch_anpr_batch
from src.web.blueprints import api


class _ArgusStub(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps({"results": [{"plate": "KA01AB1234"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


class _StubServer(ThreadingHTTPServer):
    request_queue_size = 128  # stdlib default 5 drops connections under load


@pytest.fixture
def argus_url():
    srv = _StubServer(("127.0.0.1", 0), _ArgusStub)
    srv.daemon_threads = True
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/recognize"
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=2.0)


def test_argus_probe_runs_once_under_concurrent_status_calls(monkeypatch):
    calls: list[str] = []

    def slow_probe(url: str) -> bool:
        calls.append(url)
        time.sleep(0.2)
        return True

    monkeypatch.setattr(api, "_check_argus_online", slow_probe)
    monkeypatch.setattr(api, "_last_argus_check_time", float("-inf"))
    monkeypatch.setattr(api, "_last_argus_online_status", False)
    start = threading.Barrier(16, timeout=5.0)

    def status() -> bool:
        start.wait()
        return api._get_cached_argus_status("http://127.0.0.1:8000/recognize")

    with ThreadPoolExecutor(16) as ex:
        results = list(ex.map(lambda _: status(), range(16)))

    assert len(calls) == 1  # unlocked: every /api/status thread probes Argus at once
    assert all(isinstance(r, bool) for r in results)
    assert True in results
    assert api._last_argus_online_status is True


def test_shared_http_session_is_safe_across_anpr_workers(argus_url):
    recorded: list[tuple[str | None, str]] = []
    lock = threading.Lock()

    def record(_sid: str, _cam: int, plate: str | None, status: str) -> None:
        with lock:
            recorded.append((plate, status))

    with requests.Session() as session, ThreadPoolExecutor(8) as pool:
        batch = [(i % 4 + 1, b"\xff\xd8" + bytes(20_000)) for i in range(400)]
        futures = dispatch_anpr_batch(pool, "SESS", batch, server_url=argus_url, callback=record, session=session)
        results = [f.result(timeout=10) for f in futures]

    assert results == [("KA01AB1234", "SUCCESS")] * 400
    assert len(recorded) == 400
