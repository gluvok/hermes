"""
scale.py — UART Serial Scale Indicator Driver
============================================
Handles: persistent character buffering, packet terminators (\r, \n, STX, ETX),
inter-packet timeout flush (300ms), flexible numeric extraction, and
automatic reconnect resilience for industrial deployments.
"""

from __future__ import annotations

import logging
import re
import threading
import time

import serial

from src.config import config as app_config
from src.config.constants import (
    DEFAULT_SERIAL_BAUDRATE,
    DEFAULT_SERIAL_PORT,
    INTER_CHAR_TIMEOUT_S,
    MAX_BUFFER_LEN,
    SCALE_TIMEOUT,
)

logger = logging.getLogger(__name__)


def get_current_serial_port() -> str:
    return app_config.serial_port or DEFAULT_SERIAL_PORT


def get_current_baudrate() -> int:
    return app_config.serial_baudrate or DEFAULT_SERIAL_BAUDRATE


class ScaleUARTReader:
    def __init__(self):
        self._serial: serial.Serial | None = None
        self._serial_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._stop_event.set()
        self._thread: threading.Thread | None = None
        self._line_buffer = bytearray()
        self._last_char_time = 0.0
        self._last_reconnect_attempt = 0.0
        self._lock = threading.Lock()
        self.active_port = ""
        self.active_baudrate = 0

    @property
    def _running(self) -> bool:
        return not self._stop_event.is_set()

    def start(self, port: str | None = None, baudrate: int | None = None):
        target_port = port or get_current_serial_port()
        target_baudrate = baudrate or get_current_baudrate()

        if self._thread and self._thread.is_alive():
            if self.active_port == target_port and self.active_baudrate == target_baudrate:
                return
            self.restart(target_port, target_baudrate)
            return

        self.active_port = target_port
        self.active_baudrate = target_baudrate
        self._stop_event.clear()

        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="ScaleUART")
        self._thread.start()
        logger.info(f"[Scale] UART reader thread started for {target_port} @ {target_baudrate} baud.")

    def restart(self, port: str | None = None, baudrate: int | None = None):
        """Restarts the UART reader thread with updated port and baud rate."""
        logger.info("[Scale] Restarting UART reader with updated serial configuration...")
        self.stop()
        time.sleep(0.1)
        self.start(port, baudrate)

    def stop(self):
        self._stop_event.set()
        self._close_serial()
        if self._thread and self._thread.is_alive() and self._thread != threading.current_thread():
            self._thread.join(timeout=1.5)
        self._thread = None
        logger.info("[Scale] UART reader stopped.")

    def _close_serial(self) -> None:
        with self._serial_lock:
            if self._serial:
                try:
                    if self._serial.is_open:
                        self._serial.close()
                except (serial.SerialException, OSError) as e:
                    logger.debug(f"[Scale] Error closing serial port: {e}")
                self._serial = None

    def _open_serial(self) -> bool:
        port = get_current_serial_port()
        baudrate = get_current_baudrate()
        self.active_port = port
        self.active_baudrate = baudrate
        self._close_serial()
        try:
            try:
                ser = serial.Serial(port, baudrate, timeout=SCALE_TIMEOUT, exclusive=True)
            except TypeError:
                ser = serial.Serial(port, baudrate, timeout=SCALE_TIMEOUT)
            with self._serial_lock:
                self._serial = ser
            logger.info(f"[Scale] UART opened: {port} @ {baudrate} baud")
            return True
        except (serial.SerialException, OSError) as e:
            logger.error(f"[Scale] Failed to open UART port '{port}' @ {baudrate} baud: {e}")
            self._close_serial()
            return False

    def _reconnect_if_needed(self) -> None:
        now = time.time()
        if now - self._last_reconnect_attempt >= 5.0:
            self._last_reconnect_attempt = now
            logger.info("[Scale] Attempting serial port reconnect...")
            self._open_serial()

    def _read_incoming_bytes(self) -> None:
        with self._serial_lock:
            ser = self._serial
        if ser is None or not ser.is_open:
            return

        try:
            n = getattr(ser, "in_waiting", 1) or 1
            raw = ser.read(max(1, min(n, 64)))
        except (serial.SerialException, OSError, TypeError) as e:
            if self._stop_event.is_set():
                return
            logger.error(f"[Scale] UART connection lost / read error: {e}. Reconnecting in 5s...")
            self._close_serial()
            time.sleep(1.0)
            return

        if raw:
            for b in raw:
                self.handle_scale_char(b)
        self._check_timeout_flush()

    def _read_loop(self):
        logger.info("[Scale] UART reader loop started listening for weight data...")
        self._last_reconnect_attempt = 0.0

        while not self._stop_event.is_set():
            with self._serial_lock:
                ser_is_ready = self._serial is not None and self._serial.is_open

            if not ser_is_ready:
                self._reconnect_if_needed()
                time.sleep(0.5)
                continue

            self._read_incoming_bytes()

    def handle_scale_char(self, c: str | int | bytes | bytearray):
        """
        Consumes a single character/byte or string/bytes into persistent buffer.
        Triggers parsing on packet terminators (CR, LF, STX, ETX) or when max buffer length is reached.
        """
        if isinstance(c, str):
            char_bytes = c.encode("utf-8", errors="ignore")
        elif isinstance(c, int):
            char_bytes = bytes([c])
        elif isinstance(c, (bytes, bytearray)):
            char_bytes = bytes(c)
        else:
            return

        for b in char_bytes:
            buf_to_parse = None
            with self._lock:
                self._line_buffer.append(b)
                self._last_char_time = time.time()

                # Terminators: CR (\r = 13), LF (\n = 10), STX (\x02 = 2), ETX (\x03 = 3)
                if b in (13, 10, 2, 3) or len(self._line_buffer) >= MAX_BUFFER_LEN:
                    buf_to_parse = bytes(self._line_buffer)
                    self._line_buffer.clear()

            if buf_to_parse:
                self._parse_raw_buffer(buf_to_parse)

    def _check_timeout_flush(self):
        """Flushes the line buffer if inter-character timeout (300ms) has elapsed."""
        buf_to_parse = None
        with self._lock:
            if self._line_buffer and (time.time() - self._last_char_time >= INTER_CHAR_TIMEOUT_S):
                buf_to_parse = bytes(self._line_buffer)
                self._line_buffer.clear()

        if buf_to_parse:
            self._parse_raw_buffer(buf_to_parse)

    def _parse_raw_buffer(self, buf: bytes):
        """Extracts weight numeric value from raw packet buffer and notifies stability logic."""
        if not buf:
            return

        # 1. Primary indicator protocol check: 3-6 digits followed by MN (e.g. 26500MN)
        m = re.search(rb"([0-9]{3,6})MN", buf)
        if m:
            try:
                val = float(int(m.group(1)))
                handle_scale_char_processed(val)
                return
            except ValueError:
                pass

        # 2. Fallback flexible numeric extraction (supports signed float/int e.g. +05000.5 or -12.5)
        text = buf.decode("utf-8", errors="ignore")
        m_flex = re.search(r"([-+]?\d+(?:\.\d+)?)", text)
        if m_flex:
            try:
                val = float(m_flex.group(1))
                handle_scale_char_processed(val)
                return
            except ValueError:
                pass


# Module-level singleton and callback bridge
_uart_reader = ScaleUARTReader()


def handle_scale_char(c: str | int | bytes | bytearray):
    """Called per-character/byte from external sources (for testing or alternate serial readers)."""
    _uart_reader.handle_scale_char(c)


def handle_scale_char_processed(weight: float):
    """Bridge to stability state machine — called after a weight value is extracted."""
    logger.debug(f"[Scale] Parsed weight: {weight:.3f} kg")
    from src.core.stability import process_new_weight
    process_new_weight(weight)


def get_uart_reader() -> ScaleUARTReader:
    return _uart_reader


__all__ = [
    "ScaleUARTReader",
    "get_current_baudrate",
    "get_current_serial_port",
    "get_uart_reader",
    "handle_scale_char",
    "handle_scale_char_processed",
]
