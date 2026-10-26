"""blinker.py — Background LED Color Alternator for Multistate Alerts."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.devices.led.colors import LEDColor


class LEDAlternator:
    """Toggles between two LED colors at a fixed interval in a background thread."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._stop_event.set()
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return not self._stop_event.is_set()

    def start(
        self,
        color_a: LEDColor,
        color_b: LEDColor,
        apply_fn: Callable[[LEDColor], None],
        interval: float = 1.0,
    ) -> None:
        with self._lock:
            self.stop()
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                args=(color_a, color_b, apply_fn, interval),
                name="LEDAlternator",
                daemon=True,
            )
            self._thread.start()

    def _run(
        self,
        c_a: LEDColor,
        c_b: LEDColor,
        fn: Callable[[LEDColor], None],
        interval: float,
    ) -> None:
        current = c_a
        while not self._stop_event.is_set():
            fn(current)
            if self._stop_event.wait(timeout=interval):
                break
            current = c_b if current == c_a else c_a

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive() and self._thread != threading.current_thread():
            self._thread.join(timeout=1.5)
        self._thread = None


__all__ = ["LEDAlternator"]
