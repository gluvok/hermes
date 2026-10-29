"""Unit tests for reporter module computing execution time metrics."""
from unittest import mock

from src.reporter import ExecutionReport, compute_report, log_report


def test_compute_report_empty() -> None:
    rep = compute_report([])
    assert rep.total == 0
    assert rep.success == 0
    assert rep.failed == 0
    assert rep.mean_ms == 0.0


def test_compute_report_metrics() -> None:
    # 5 samples: 10, 20, 30, 40, 50
    results = [{"execution_time_ms": float(x)} for x in (10, 20, 30, 40, 50)]
    rep = compute_report(results)
    assert rep.total == 5
    assert rep.success == 5
    assert rep.failed == 0
    assert rep.min_ms == 10.0
    assert rep.max_ms == 50.0
    assert rep.mean_ms == 30.0
    assert rep.p50_ms == 30.0
    assert rep.p95_ms == 48.0


def test_compute_report_with_failures() -> None:
    results = [
        {"execution_time_ms": 100.0},
        None,
        {"status": "error"},
        RuntimeError("Network down"),
    ]
    rep = compute_report(results)
    assert rep.total == 4
    assert rep.success == 2
    assert rep.failed == 2
    assert rep.min_ms == 100.0
    assert rep.p50_ms == 100.0


def test_log_report_emits() -> None:
    rep = ExecutionReport(
        total=1,
        success=1,
        failed=0,
        min_ms=10.0,
        max_ms=10.0,
        mean_ms=10.0,
        p50_ms=10.0,
        p95_ms=10.0,
    )
    with mock.patch("src.reporter.logger.info") as mock_log:
        log_report(rep)
        mock_log.assert_called_once()

