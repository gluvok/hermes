import pytest

from src.core.session import WeighbridgeSessionManager
from src.core.telemetry import get_system_events, reset_telemetry


@pytest.fixture
def sm():
    reset_telemetry()
    manager = WeighbridgeSessionManager()
    manager.session_id = "SESS_TEST"
    manager._anpr_statuses = ["ANPR_TIMEOUT", "ANPR_TIMEOUT", "SUCCESS"]
    yield manager
    reset_telemetry()


def test_package_includes_per_status_counts(sm):
    pkg = sm._finalize_session_package()

    assert pkg["anpr_status_counts"] == {"ANPR_TIMEOUT": 2, "SUCCESS": 1}


def test_status_counts_reach_telemetry_events(sm):
    sm._finalize_session_package()

    anpr_events = [e for e in get_system_events() if e["source"] == "ANPR"]
    assert len(anpr_events) == 1
    assert "SESS_TEST" in anpr_events[0]["message"]
    assert "'ANPR_TIMEOUT': 2" in anpr_events[0]["message"]
    assert "'SUCCESS': 1" in anpr_events[0]["message"]
