"""controller.py — RGB LED State Machine Controller."""

from __future__ import annotations

import logging
import threading
import time

from src.devices.led.blinker import LEDAlternator
from src.devices.led.colors import LEDColor
from src.devices.led.driver import LEDHardwareDriver

logger = logging.getLogger(__name__)


class RGBLedController:
    """Orchestrates LED states: Green, Yellow, Red, Blue, and alternating Red/Yellow."""

    def __init__(
        self,
        driver: LEDHardwareDriver | None = None,
        alternator: LEDAlternator | None = None,
    ) -> None:
        self.driver = driver or LEDHardwareDriver()
        self.alternator = alternator or LEDAlternator()
        self._current_color = LEDColor.OFF
        self._is_active_session = False
        self._is_online = True
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    @property
    def current_color(self) -> LEDColor:
        return self._current_color

    @property
    def is_online(self) -> bool:
        return self._is_online

    def _get_idle_color(self) -> LEDColor:
        return LEDColor.GREEN if self._is_online else LEDColor.YELLOW

    def _apply_color(self, color: LEDColor) -> None:
        self._current_color = color
        self.driver.set_rgb(*color.value)
        logger.info(f"[LED] State changed to {color.name}")

    def startup_test(self, delay: float = 1.0) -> None:
        """Cycles Green -> Red -> Blue (delay seconds each), then resets to idle."""
        logger.info(f"[LED] Starting hardware sequence: Green -> Red -> Blue ({delay}s each)...")
        for color in (LEDColor.GREEN, LEDColor.RED, LEDColor.BLUE):
            with self._lock:
                self._apply_color(color)
            time.sleep(delay)
        self.set_idle()

    def set_idle(self) -> None:
        """Sets LED to Green (if online) or Yellow (if offline) when scale returns to zero."""
        self.alternator.stop()
        with self._lock:
            self._is_active_session = False
            if self._timer is None:
                self._apply_color(self._get_idle_color())

    def set_network_status(self, is_online: bool) -> None:
        """Updates network status; toggles Red/Yellow if weighing, else idle color."""
        with self._lock:
            self._is_online = is_online
            if self._is_active_session:
                self._update_active_weighment_led()
            elif self._timer is None:
                self._apply_color(self._get_idle_color())

    def set_active(self) -> None:
        """Sets LED when vehicle weight detected: Red (online) or alternating Red/Yellow (offline)."""
        with self._lock:
            self._is_active_session = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._update_active_weighment_led()

    def _update_active_weighment_led(self) -> None:
        """Sets solid Red if online or starts alternating Red/Yellow if offline."""
        if self._is_online:
            self.alternator.stop()
            self._apply_color(LEDColor.RED)
        else:
            self.alternator.start(
                LEDColor.RED,
                LEDColor.YELLOW,
                self._apply_color,
                interval=1.0,
            )

    def trigger_cloud_success(self, duration: float = 10.0) -> None:
        """Turns LED Blue for duration (seconds) after cloud upload success."""
        self.alternator.stop()
        with self._lock:
            self._is_active_session = False
            if self._timer is not None:
                self._timer.cancel()
            self._apply_color(LEDColor.BLUE)
            self._timer = threading.Timer(duration, self._on_success_timeout)
            self._timer.daemon = True
            self._timer.start()

    def _on_success_timeout(self) -> None:
        with self._lock:
            self._timer = None
            self._is_active_session = False
            self._apply_color(self._get_idle_color())

    def cleanup(self) -> None:
        """Cancels timers and alternator, and turns off LED."""
        self.alternator.stop()
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._apply_color(LEDColor.OFF)
        self.driver.close()
