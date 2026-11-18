# Hermes Codebase Technical Reference

Comprehensive API, module, and subsystem reference for maintaining and extending the Hermes edge controller.

---

## 1. System Overview

`hermes` runs on a Raspberry Pi 5 under Python 3.14 (free-threaded CPython). It orchestrates:
- RS-232 / UART serial stream reading from industrial weighbridge indicators.
- Synchronized multi-camera frame grabbing and in-memory pre-compression.
- Argus ANPR REST microservice integration with consensus candidate voting.
- Local SQLite store-and-forward persistence in WAL mode for network drop durability.
- Linux NetworkManager captive portal and fallback emergency access point.
- Gluvok Cloud API multipart synchronization.

---

## 2. Root Architecture & Entry Points

### `main.py`
Process lifecycle daemon and signal orchestration.
- **`shutdown(signum, frame) -> None`**: Handles `SIGINT` and `SIGTERM`. Gracefully halts `stop_spool_worker()`, `led_controller.cleanup()`, `get_uart_reader().stop()`, `stop_web_server()`, and `stop_wifi_watchdog()`.
- **`setup() -> None`**: Starts UART reader, diagnostics web server (`FallbackWebServer`), Wi-Fi watchdog, SQLite database (`init_db()`), and background queue drain worker (`start_spool_worker(10.0)`).
- **`loop() -> None`**: Ticks every 1 second; triggers `session_manager.check_session_progress()` to ensure completion even during scale serial silence.

### `scripts/`
- **`build.py`**: Nuitka native binary compilation script.
- **`deploy.py`**: Automated SSH deployment, building, and systemd service provisioning.
- **`keygen.py`**: Ed25519 digital signature keypair generation and client license creator.
- **`wifi_setup.py`**: Standalone command-line Wi-Fi network scanner and connector.
- **`audit_credentials.py`**: Static security scanner verifying zero hardcoded credentials.

---

## 3. Configuration Subsystem (`src/config/`)

- **`client_config.py`**: Base hardware and cloud settings loaded from environment variables with fallbacks. Contains zero hardcoded passwords or RTSP credentials.
- **`constants.py`**: Central system constants: timing windows, buffer limits, default ports, and Indian vehicle registration regex.
- **`manager.py` (`ConfigManager`)**: Unified thread-safe accessor exposing runtime properties with fallback to `client_config` and `data/client.lic`.
- **`runtime.py` (`RuntimeConfig`)**: Manages dynamic runtime configuration overrides in SQLite under `threading.RLock()`.
- **`store.py`**: Low-level SQLite operations for the `runtime_config` key-value table.
- **`license.py`**: Ed25519 cryptographic license verification ensuring client license authenticity without cloud connectivity.

---

## 4. Core Logic Subsystem (`src/core/`)

### `src/core/db.py`
SQLite initialization and thread connection factory.
- **`init_db(db_path=None) -> None`**: Configures SQLite database (`data/hermes.db`) with `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, and `PRAGMA busy_timeout = 5000`. Creates `wifi_networks` and `weighment_queue` tables.
- **`_get_connection() -> sqlite3.Connection`**: Thread-safe connection getter with row factory.

### `src/core/spool.py`
SQLite FIFO store-and-forward queue ensuring local data durability during internet outages.
- **`enqueue_weighment(session_id: str, payload: dict) -> bool`**: Inserts completed weighment payload into `weighment_queue` with status `PENDING`.
- **`get_pending_weighments(limit: int = 20) -> list[dict]`**: Retrieves pending weighments sorted by creation time.
- **`mark_weighment_completed(session_id: str) -> bool`**: Removes confirmed weighment from queue.
- **`mark_weighment_failed(session_id: str, error: str) -> bool`**: Increments retry count and records error message.
- **`spool_queue_count() -> int`**: Returns number of pending weighments.
- **`drain_spool_queue() -> int`**: Transmits pending weighments to Gluvok API sequentially when Wi-Fi is connected.
- **`start_spool_worker(interval: float = 10.0) -> None`**: Starts background queue drain daemon thread.
- **`stop_spool_worker() -> None`**: Stops background queue drain worker.

### `src/core/session.py`
Weighbridge session lifecycle coordinator (`WeighbridgeSessionManager`).
- **`SessionPhase`**: `PHASE_IDLE` (0), `PHASE_STABILIZING` (1), `PHASE_POST_STABILITY` (2), `PHASE_COMPLETED` (3).
- **`start_session() -> None`**: Spawns 1-second ANPR frame capture loop.
- **`trigger_mid_stability_fleet_capture() -> None`**: Asynchronously acquires all overview camera snapshots halfway through the stability window and pre-compresses them to JPEG in RAM.
- **`on_weight_stabilized(weight: float) -> None`**: Starts post-stability countdown.
- **`check_session_progress() -> dict | None`**: Finalizes session package upon countdown expiration without blocking on slow ANPR microservice responses.
- **`reset_session() -> None`**: Clears session state when weight returns to zero.

### `src/core/stability.py`
Continuous weight stability state machine (`ScaleStabilityMachine`).
- Tracks weight readings within `stability_tolerance` (±2.0 kg) across `stability_duration` (10.0 s).
- When stable, packages session and dispatches upload:
  - If online, posts directly to Gluvok Cloud API via background thread.
  - If offline, enqueues package to SQLite store-and-forward queue via `enqueue_weighment`.

### `src/core/telemetry.py`
Decoupled, thread-safe in-memory circular telemetry and error histogram buffer.

### `src/core/wifi_vault.py`
SQLite-backed persistent credentials store for known Wi-Fi networks in `wifi_networks`.

---

## 5. Devices Subsystem (`src/devices/`)

### `src/devices/scale.py`
Scale UART stream reader (`ScaleUARTReader`).
- Reads raw serial stream on `/dev/ttyAMA0` or USB serial at configured baud rate.
- Inter-character silence timer (300ms) flushes stale partial frames.
- Packet framing parser extracts numeric weights using regex patterns and standard delimiters (`\r`, `\n`, STX, ETX).

### `src/devices/camera.py`
Camera snapshot acquisition and JPEG compression.
- **`fetch_image_bytes(url, timeout)`**: Fetches image from HTTP snapshot endpoint or RTSP stream via OpenCV.
- **`capture_all_camera_snapshots(urls)`**: Concurrently grabs snapshots from all configured cameras using `ThreadPoolExecutor`.
- **`compress_image_bytes(data, quality=85, max_dimension=1920)`**: In-memory JPEG optimization resizing images exceeding 1920px while preserving aspect ratio.

### `src/devices/wifi/`
NetworkManager Wi-Fi management and RFC captive portal subsystem.
- **`manager.py`**: Upstream Wi-Fi connection, periodic network scanning, emergency fallback hotspot, and watchdog loop.
- **`portal.py`**: Captive portal HTTP server, DNS request interceptor, RFC 8910 (DHCP Option 114), and RFC 8908 API endpoint (`/capport`).
- **`runner.py`**: Subprocess command runner with `SIMULATION_STATE["enabled"]` switch for hardware-independent unit testing.
- **`state.py`**: Thread-safe lock-guarded Wi-Fi operational flags.

### `src/devices/led/`
RGB status LED controller (`python-periphery` GPIO on pins 17, 27, 22).

---

## 6. Integrations Subsystem (`src/integrations/`)

### `src/integrations/anpr.py`
Argus ANPR REST microservice client.
- Submits JPEG frames asynchronously to `/recognize`.
- Associates recognition requests with unique `session_id` tags to discard late responses.
- Elects consensus license plate candidate using frequency voting (`get_highest_frequency_plate`).

### `src/integrations/gluvok.py`
Gluvok Cloud API client.
- Submits multipart/form-data weighment records with HTTP Basic Authentication (`device_id:device_key`).
- Attaches multi-camera JPEG files (`anpr_1`, `anpr_2`, `aux_1`).
- Implements verify-before-retry protocol to prevent duplicate entries upon network timeouts.

---

## 7. Web Diagnostics Subsystem (`src/web/`)

- **`app.py`**: Flask application factory with security headers (`nosniff`, `DENY`) and JSON error handlers.
- **`auth.py`**: Token-based session management, sliding 2-hour expiration, and brute-force protection (max 5 failed logins per 60s). Password configured via `SUPERADMIN_PASS`.
- **`validation.py`**: URL and configuration schema validation.
- **`server.py` (`FallbackWebServer`)**: Werkzeug WSGI server running on background daemon thread at port 8080.
- **`blueprints/`**:
  - `views.py`: Dashboard single-page routes.
  - `api.py`: Telemetry (`/api/status`), Wi-Fi provisioning (`/api/wifi`), and configuration (`/api/config`) REST endpoints.

---

## 8. Test Suite & Verification

The test suite runs with 100% hardware isolation in `tests/conftest.py`:
- `ScaleUARTReader` background threads mocked.
- Direct `sudo`, `iptables`, and `fuser` calls intercepted.
- OpenCV RTSP stream network calls mocked.

Run tests:
```bash
uv run pytest -v
```
