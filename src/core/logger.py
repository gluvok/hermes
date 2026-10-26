"""logger.py — Terminal ANSI color formatter for real-time observability."""

from __future__ import annotations

import logging
import sys

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"

LEVEL_COLORS = {
    logging.DEBUG: DIM + CYAN,
    logging.INFO: GREEN,
    logging.WARNING: YELLOW,
    logging.ERROR: RED,
    logging.CRITICAL: BOLD + RED,
}


class ColoredFormatter(logging.Formatter):
    """Custom logging formatter injecting ANSI colors for terminal log visibility."""

    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelno, RESET)
        asctime = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()

        if "[ANPR]" in msg or "[Argus" in msg:
            if "Plate detected" in msg or "Plate='" in msg:
                msg = f"{BOLD}{GREEN}{msg}{RESET}"
            elif "No plate" in msg:
                msg = f"{YELLOW}{msg}{RESET}"
            elif "[Argus Complete Response]" in msg or "[Argus Response]" in msg:
                msg = f"{BRIGHT_CYAN}{msg}{RESET}"
            else:
                msg = f"{BRIGHT_MAGENTA}{msg}{RESET}"

        return f"{DIM}{asctime}{RESET} [{color}{record.levelname:<5s}{RESET}] {msg}"


def setup_colored_logging(level: int = logging.INFO) -> None:
    """Configures root logger with ColoredFormatter outputting to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


__all__ = ["ColoredFormatter", "setup_colored_logging"]
