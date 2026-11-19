import signal
import threading
import time
import unittest
from unittest.mock import MagicMock

from src.core.shutdown import GracefulShutdownDrain


class TestShutdownDrain(unittest.TestCase):
    def test_drain_handler_waits_for_inflight_session(self):
        drain = GracefulShutdownDrain(grace_period=2.0)
        self.assertFalse(drain.is_shutting_down)

        # Simulate active weighment session
        drain.begin_session("sess-123")
        self.assertTrue(drain.has_active_session)

        # Trigger shutdown signal
        drain.request_shutdown(signum=signal.SIGTERM)
        self.assertTrue(drain.is_shutting_down)

        # In-flight session completes after 0.2s
        def complete_later():
            time.sleep(0.2)
            drain.end_session("sess-123")

        t = threading.Thread(target=complete_later)
        t.start()

        completed = drain.wait_for_drain()
        t.join()
        self.assertTrue(completed)
        self.assertFalse(drain.has_active_session)

    def test_drain_handler_closes_serial_handle_cleanly(self):
        drain = GracefulShutdownDrain(grace_period=1.0)
        mock_serial = MagicMock()
        drain.register_cleanup_hook("serial_port", mock_serial.close)

        drain.request_shutdown(signum=signal.SIGINT)
        drain.wait_for_drain()

        mock_serial.close.assert_called_once()

    def test_drain_handler_timeout_fallback(self):
        drain = GracefulShutdownDrain(grace_period=0.1)
        drain.begin_session("sess-hang")
        drain.request_shutdown(signum=signal.SIGTERM)
        # Session does not complete before grace_period
        completed = drain.wait_for_drain()
        self.assertFalse(completed)
        self.assertTrue(drain.has_active_session)
