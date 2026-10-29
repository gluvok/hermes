"""Execution metrics aggregation and reporting."""
import math
import statistics
from dataclasses import dataclass
from typing import Any

from loguru import logger


@dataclass(frozen=True)
class ExecutionReport:
    total: int
    success: int
    failed: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float


def _calc_p95(s: list[float]) -> float:
    if not s:
        return 0.0
    k = (len(s) - 1) * 0.95
    f, c = math.floor(k), math.ceil(k)
    return s[f] if f == c else s[f] * (c - k) + s[c] * (k - f)


def compute_report(results: list[Any]) -> ExecutionReport:
    times = [
        float(r["execution_time_ms"])
        for r in results
        if isinstance(r, dict) and isinstance(r.get("execution_time_ms"), (int, float))
    ]
    succ = sum(1 for r in results if isinstance(r, dict))
    total = len(results)
    s = sorted(times)
    return ExecutionReport(
        total=total,
        success=succ,
        failed=total - succ,
        min_ms=min(s) if s else 0.0,
        max_ms=max(s) if s else 0.0,
        mean_ms=statistics.mean(s) if s else 0.0,
        p50_ms=statistics.median(s) if s else 0.0,
        p95_ms=_calc_p95(s),
    )


def log_report(rep: ExecutionReport) -> None:
    logger.info(
        f"\n--- Execution Time Report (ms) ---\n"
        f"Total: {rep.total} | Success: {rep.success} | Failed: {rep.failed}\n"
        f"Min: {rep.min_ms:.2f} ms | Max: {rep.max_ms:.2f} ms\n"
        f"Mean: {rep.mean_ms:.2f} ms | P50: {rep.p50_ms:.2f} ms | P95: {rep.p95_ms:.2f} ms"
    )
