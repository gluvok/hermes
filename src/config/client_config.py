"""client_config.py — Bespoke client deployment configuration."""
from __future__ import annotations

# Cloud credentials: no committed defaults; supplied by data/client.lic (#33)
DEVICE_ID: str | int = ""
DEVICE_KEY: str = ""
CENTER_ID: int = 1

# Weighment & OCR thresholds (compiled into binary, non-configurable via UI)
MIN_WEIGHT: float = 200.0
ANPR_SERVER_URL: str = "http://127.0.0.1:8000/recognize"

# Baseline hardware settings (overridable via Web UI, stored in SQLite)
SERIAL_PORT: str = "/dev/ttyAMA0"
SERIAL_BAUDRATE: int = 2400
STABILITY_DURATION: float = 10.0
STABILITY_TOLERANCE: float = 2.0
ANPR_CAMERA_URLS: list[str] = []
AUXILIARY_CAMERA_URLS: list[str] = []

# Wi-Fi credentials: empty until set via Web UI (stored in SQLite)
WIFI_SSID: str = ""
WIFI_PASSWORD: str = ""
