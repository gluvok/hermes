"""test_logger.py — Unit Tests for Terminal ANSI Colored Formatter."""

from __future__ import annotations

import logging
import unittest

from src.core.logger import ColoredFormatter, setup_colored_logging


class TestColoredFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = ColoredFormatter()
        self._orig_level = logging.getLogger().level
        self._orig_handlers = list(logging.getLogger().handlers)

    def tearDown(self):
        root = logging.getLogger()
        root.setLevel(self._orig_level)
        root.handlers = self._orig_handlers

    def test_format_info_level_contains_ansi_colors(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="System started successfully",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertIn("INFO", formatted)
        self.assertIn("\033[", formatted)
        self.assertIn("System started successfully", formatted)

    def test_format_anpr_plate_detected_highlighted_green(self):
        record = logging.LogRecord(
            name="src.integrations.anpr",
            level=logging.INFO,
            pathname="anpr.py",
            lineno=50,
            msg="[ANPR] Camera 1: Plate detected: 'MH12AB1234'",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertIn("MH12AB1234", formatted)
        self.assertIn("\033[32m", formatted)

    def test_format_anpr_no_plate_highlighted_yellow(self):
        record = logging.LogRecord(
            name="src.integrations.anpr",
            level=logging.INFO,
            pathname="anpr.py",
            lineno=50,
            msg="[ANPR] Camera 1: No plate detected",
            args=(),
            exc_info=None,
        )
        formatted = self.formatter.format(record)
        self.assertIn("No plate detected", formatted)
        self.assertIn("\033[33m", formatted)

    def test_setup_colored_logging_configures_root_logger(self):
        setup_colored_logging(level=logging.DEBUG)
        root = logging.getLogger()
        self.assertEqual(root.level, logging.DEBUG)
        self.assertTrue(any(isinstance(h.formatter, ColoredFormatter) for h in root.handlers))


if __name__ == "__main__":
    unittest.main()
