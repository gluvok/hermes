"""client_config.py — Bespoke client deployment configuration."""
from __future__ import annotations

# Cloud credentials (compiled into binary, non-configurable via UI)
DEVICE_ID: str | int = "pi0"
DEVICE_KEY: str = "hardware123"
CENTER_ID: int = 3

# Weighment & OCR thresholds (compiled into binary, non-configurable via UI)
MIN_WEIGHT: float = 70.0
ANPR_SERVER_URL: str = "http://127.0.0.1:8000/recognize"

# Baseline hardware settings (overridable via Web UI, stored in SQLite)
SERIAL_PORT: str = "/dev/ttyAMA0"
SERIAL_BAUDRATE: int = 2400
STABILITY_DURATION: float = 10.0
STABILITY_TOLERANCE: float = 2.0
ANPR_CAMERA_URLS: list[str] = [
    "rtsp://admin:AbcMeerut%40123@192.168.10.250:554/video/live?channel=1&subtype=0",
    "rtsp://admin:AbcMeerut%40123@192.168.10.251:554/video/live?channel=1&subtype=0",
]
AUXILIARY_CAMERA_URLS: list[str] = [
    "rtsp://admin:AbcMeerut%40123@192.168.10.252:554/video/live?channel=1&subtype=0",
]

# Baseline Wi-Fi credentials (overridable via Web UI, stored in SQLite)
WIFI_SSID: str = "TestRouter_5G"
WIFI_PASSWORD: str = "SecretPassword123"
