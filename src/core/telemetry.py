"""
telemetry.py — Core System Events & Weighment Telemetry Store
============================================================
Decoupled, thread-safe central telemetry buffer. Stores:
- Circular system events log (max 20 entries)
- Latest weighment session outcome
- Live error frequency counters
"""

from __future__ import annotations

import threading
import time
from typing import Any

_system_events: list[dict[str, str]] = []
_events_lock = threading.Lock()

_latest_weighment: dict[str, Any] = {
    "session_id": None,
    "plate": None,
    "weight": 0.0,
    "timestamp": None,
    "is_error": False,
    "status_code": "READY",
}
_error_counts: dict[str, int] = {}
# Weighments lost for good: discarded offline, rejected with a 400, or the outbox was full or unwritable.
_unsent_weighments = 0
# Weighments waiting in the SQLite outbox for a later retry (published by src.core.outbox).
_outbox_pending = 0
# Consecutive 401/403 replies from the cloud; the next accepted upload clears the streak.
_cloud_auth_failures = 0
_live_lock = threading.Lock()


def record_system_event(source: str, message: str) -> None:
    """Appends an event to the circular telemetry log (max 20 entries)."""
    with _events_lock:
        if len(_system_events) >= 20:
            _system_events.pop(0)
        _system_events.append({
            "time": time.strftime("%H:%M:%S"),
            "source": source,
            "message": message,
        })


def record_weighment_result(
    session_id: str,
    plate: str,
    weight: float,
    is_error: bool = False,
    status_code: str = "SUCCESS",
) -> None:
    """Records the latest weighbridge session outcome and updates live error counters."""
    with _live_lock:
        _latest_weighment["session_id"] = session_id
        _latest_weighment["plate"] = plate
        _latest_weighment["weight"] = weight
        _latest_weighment["timestamp"] = time.strftime("%H:%M:%S")
        _latest_weighment["is_error"] = is_error
        _latest_weighment["status_code"] = status_code

        if is_error or status_code not in ("SUCCESS", "READY"):
            _error_counts[status_code] = _error_counts.get(status_code, 0) + 1


def record_error_event(error_code: str, message: str = "") -> None:
    """Explicitly increments live occurrence count for a system error code."""
    with _live_lock:
        _error_counts[error_code] = _error_counts.get(error_code, 0) + 1


def record_unsent_weighment() -> None:
    """Counts one weighment that was dropped instead of reaching the cloud (#18)."""
    global _unsent_weighments
    with _live_lock:
        _unsent_weighments += 1


def get_unsent_weighment_count() -> int:
    """Returns how many weighments were dropped since startup."""
    with _live_lock:
        return _unsent_weighments


def set_outbox_pending(count: int) -> None:
    """Publishes the outbox size so /api/status never touches SQLite."""
    global _outbox_pending
    with _live_lock:
        _outbox_pending = count


def get_outbox_pending() -> int:
    """Returns how many weighments are queued for retry."""
    with _live_lock:
        return _outbox_pending


def record_cloud_auth(accepted: bool) -> None:
    """Tracks the 401/403 streak; an accepted upload clears it."""
    global _cloud_auth_failures
    with _live_lock:
        _cloud_auth_failures = 0 if accepted else _cloud_auth_failures + 1


def get_cloud_auth_failures() -> int:
    """Returns the current run of consecutive 401/403 replies."""
    with _live_lock:
        return _cloud_auth_failures


def get_latest_weighment() -> dict[str, Any]:
    """Returns a snapshot of the latest weighment status."""
    with _live_lock:
        return dict(_latest_weighment)


def get_error_counts() -> dict[str, int]:
    """Returns a snapshot of active error counts."""
    with _live_lock:
        return dict(_error_counts)


def get_system_events() -> list[dict[str, str]]:
    """Returns a copy of the circular telemetry event buffer."""
    with _events_lock:
        return list(_system_events)


def reset_telemetry() -> None:
    """Resets in-memory telemetry buffers (useful for testing and reset flows)."""
    global _unsent_weighments, _outbox_pending, _cloud_auth_failures
    with _events_lock:
        _system_events.clear()
    with _live_lock:
        _unsent_weighments = 0
        _outbox_pending = 0
        _cloud_auth_failures = 0
        _latest_weighment["session_id"] = None
        _latest_weighment["plate"] = None
        _latest_weighment["weight"] = 0.0
        _latest_weighment["timestamp"] = None
        _latest_weighment["is_error"] = False
        _latest_weighment["status_code"] = "READY"
        _error_counts.clear()


# Convenience alias matching legacy tests/callers
reset_state = reset_telemetry

__all__ = [
    "get_cloud_auth_failures",
    "get_error_counts",
    "get_latest_weighment",
    "get_outbox_pending",
    "get_system_events",
    "get_unsent_weighment_count",
    "record_cloud_auth",
    "record_error_event",
    "record_system_event",
    "record_unsent_weighment",
    "record_weighment_result",
    "reset_state",
    "reset_telemetry",
    "set_outbox_pending",
]
