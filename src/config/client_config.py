"""client_config.py — Bespoke client deployment configuration."""

from __future__ import annotations

import os

# Cloud credentials (compiled into binary, non-configurable via UI)
DEVICE_ID: str | int = os.getenv("DEVICE_ID", "pi1")
DEVICE_KEY: str = os.getenv("DEVICE_KEY", "")
CENTER_ID: int = int(os.getenv("CENTER_ID", "1"))

# Weighment & OCR thresholds (compiled into binary, non-configurable via UI)
MIN_WEIGHT: float = float(os.getenv("MIN_WEIGHT", "200.0"))
ANPR_SERVER_URL: str = os.getenv("ANPR_SERVER_URL", "http://127.0.0.1:8000/recognize")

# Baseline hardware settings (overridable via Web UI, stored in SQLite)
SERIAL_PORT: str = os.getenv("SERIAL_PORT", "/dev/ttyAMA0")
SERIAL_BAUDRATE: int = int(os.getenv("SERIAL_BAUDRATE", "2400"))
STABILITY_DURATION: float = float(os.getenv("STABILITY_DURATION", "10.0"))
STABILITY_TOLERANCE: float = float(os.getenv("STABILITY_TOLERANCE", "2.0"))
ANPR_CAMERA_URLS: list[str] = [
    os.getenv("CAMERA_ANPR_1_URL", "rtsp://camera-anpr-1.local:554/live"),
    os.getenv("CAMERA_ANPR_2_URL", "rtsp://camera-anpr-2.local:554/live"),
]
AUXILIARY_CAMERA_URLS: list[str] = [
    os.getenv("CAMERA_AUX_1_URL", "rtsp://camera-aux-1.local:554/live"),
]

# Baseline Wi-Fi credentials (overridable via Web UI, stored in SQLite)
WIFI_SSID: str = os.getenv("WIFI_SSID", "")
WIFI_PASSWORD: str = os.getenv("WIFI_PASSWORD", "")
