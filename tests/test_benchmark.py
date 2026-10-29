"""Unit tests for benchmark entrypoint orchestration."""
import asyncio
from unittest import mock

import benchmark


def test_benchmark_async_main() -> None:
    mock_payload = [{"execution_time_ms": 100.0}]
    with (
        mock.patch("benchmark.load_images_to_memory", return_value=[]),
        mock.patch("benchmark.run_streamer", return_value=mock_payload),
        mock.patch("benchmark.compute_report") as mock_comp,
        mock.patch("benchmark.log_report") as mock_log,
    ):
        asyncio.run(benchmark.async_main())
        mock_comp.assert_called_once_with(mock_payload)
        mock_log.assert_called_once()


def test_benchmark_main_success() -> None:
    with mock.patch("benchmark.async_main", return_value=None) as mock_async:
        benchmark.main()
        mock_async.assert_called_once()


def test_benchmark_main_keyboard_interrupt() -> None:
    with mock.patch(
        "benchmark.async_main", side_effect=KeyboardInterrupt
    ):
        # Should exit gracefully without raising
        benchmark.main()

