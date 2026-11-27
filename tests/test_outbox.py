from src.core import db, outbox


def test_outbox_is_fifo_and_parks_failed_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_db_path", str(tmp_path / "q.db"))
    k1 = outbox.enqueue(1, "MH12AB1234", 100.5, [("truck_a.jpg", b"\xff\xd8a")])
    k2 = outbox.enqueue(1, "", 200.0, [])
    assert k1 != k2

    first = outbox.peek_oldest()
    assert first is not None
    assert first["idempotency_key"] == k1
    assert first["images"] == [("truck_a.jpg", b"\xff\xd8a")]

    outbox.mark_failed(first["id"])
    second = outbox.peek_oldest()
    assert second is not None and second["idempotency_key"] == k2

    outbox.remove(second["id"])
    assert outbox.peek_oldest() is None
