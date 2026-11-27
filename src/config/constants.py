"""constants.py — Centralized System & Hardware Constants."""
from __future__ import annotations

import os

INTER_CHAR_TIMEOUT_S = 0.3
MAX_BUFFER_LEN = 256
SCALE_TIMEOUT = 0.05
DEFAULT_SERIAL_PORT = "/dev/ttyAMA0"

STABILITY_TOLERANCE = 2.0
STABILITY_DURATION = 10.0

ANPR_CAPTURE_INTERVAL = 1.0
POST_STABILITY_DURATION = 5.0
CAMERA_TIMEOUT = 3.0
ANPR_SERVER_TIMEOUT = float(os.environ.get("ANPR_SERVER_TIMEOUT", "30.0"))
ANPR_MAX_IN_FLIGHT = 2
ANPR_WORKERS = 2
MAX_PARALLEL_CAMERA_WORKERS = 4

GLUVOK_BASE_URL = os.environ.get("GLUVOK_BASE_URL", "https://gluvok.vercel.app").rstrip("/")
CLOUD_POST_TIMEOUT = 20.0
CLOUD_POST_RETRIES = 3  # retries after the first attempt
CLOUD_RETRY_AFTER_MAX_S = 60  # janus sends <=60 s; never park an upload thread longer for a stray proxy
CLOUD_MAX_IMAGES = 3  # janus ingest rejects more than 3 file parts
CLOUD_AUTH_ALERT_THRESHOLD = 3  # consecutive 401/403 replies before /api/status flags auth_failing
OUTBOX_MAX_ROWS = 500  # ~250 KB per weighment: bounds the outbox near 125 MB of SD card
OUTBOX_DRAIN_INTERVAL_S = 30.0
DEFAULT_CENTER_ID = 1

DEFAULT_DB_PATH = "data/hermes.db"

DEFAULT_LED_PIN_RED = 17
DEFAULT_LED_PIN_GREEN = 27
DEFAULT_LED_PIN_BLUE = 22
DEFAULT_LED_ACTIVE_HIGH = False
LED_CLOUD_SUCCESS_DURATION = 10.0
