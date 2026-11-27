# Hermes Codebase Reference

Module-by-module map of the code. For behavior and data flow, read [ARCHITECTURE.md](ARCHITECTURE.md) first.

## Layout

```
main.py                 Entry point: setup(), loop(), thread supervision, shutdown
wifi_setup.py           Standalone CLI: --scan, --connect, --hotspot
run.sh                  Launcher: bin/hermes if built, else uv run, else python3
scripts/                build.py (Nuitka), deploy.py, keygen.py, package.py
src/config/             Settings, license, SQLite overrides
src/core/               Session, stability machine, telemetry, DB init, Wi-Fi vault, logging
src/devices/            scale.py, camera.py, led/, wifi/
src/integrations/       anpr.py (Argus), gluvok.py (cloud)
src/services/           image_compressor.py
src/web/                Flask app, auth, validation, blueprints, templates, static
tests/                  pytest suite
```

## Entry point: `main.py`

- `setup()`: `require_runtime_secrets()`, LED startup test, start UART reader, web server (`:8080`) and Wi-Fi watchdog, `init_db()`, log config and camera fleet.
- `loop()`: every 1 s calls `_supervise_threads()` (restarts a dead UART reader or watchdog), then `session_manager.check_session_progress()` and uploads a finished package.
- `SIGINT`/`SIGTERM`: cleanup LED, UART, web server, watchdog, hotspot, session.

## `src/config/`

| File | Contents |
| :--- | :--- |
| `client_config.py` | Defaults: empty `DEVICE_ID`/`DEVICE_KEY`, `CENTER_ID=1`, `MIN_WEIGHT=200.0`, `ANPR_SERVER_URL`, `SERIAL_PORT=/dev/ttyAMA0`, `SERIAL_BAUDRATE=2400`, stability 10 s / 2 kg, empty camera lists |
| `constants.py` | Timing and size constants (below), `GLUVOK_BASE_URL`, `DEFAULT_DB_PATH=data/hermes.db`, LED pins |
| `license.py` | `sign_license`, `verify_license` (Ed25519), `load_client_license` (returns `None` if the file is missing or invalid) |
| `store.py` | `runtime_config` table: `load_overrides`, `set_override` |
| `runtime.py` | `RuntimeConfig`: locked in-memory view of overrides, `update_system`, `update_wifi`, `clear_wifi` |
| `manager.py` | `ConfigManager` (the `config` singleton): licensed values first, then `client_config`; runtime values from `RuntimeConfig` |

Constants: `INTER_CHAR_TIMEOUT_S=0.3`, `MAX_BUFFER_LEN=256`, `SCALE_TIMEOUT=0.05`, `STABILITY_DURATION=10.0`, `STABILITY_TOLERANCE=2.0`, `ANPR_CAPTURE_INTERVAL=1.0`, `POST_STABILITY_DURATION=5.0`, `CAMERA_TIMEOUT=3.0`, `ANPR_SERVER_TIMEOUT=30.0`, `MAX_PARALLEL_CAMERA_WORKERS=4`, `CLOUD_POST_TIMEOUT=20.0`, `LED_CLOUD_SUCCESS_DURATION=10.0`.

## `src/core/`

- **`session.py`**: `WeighbridgeSessionManager` (singleton `session_manager`). Phases: `PHASE_IDLE`, `PHASE_STABILIZING`, `PHASE_POST_STABILITY`, `PHASE_COMPLETED`.
  - `start_session()`: new `SESS_<time>_<hex>` ID, worker pool, HTTP session, `ANPRLoop_<id>` thread.
  - `record_anpr_result(session_id, cam_idx, plate, status)`: stores a plate and its status; ignores results from a previous session.
  - `trigger_mid_stability_fleet_capture()`, `on_weight_stabilized(weight)`: start `FleetCapture_<id>`.
  - `check_session_progress()`: after 5 s post-stability, marks completed and returns the package.
  - Package keys: `session_id`, `weight`, `anpr_plate`, `camera_snapshots`, `total_anpr_samples`, `total_anpr_frames`, `anpr_status_counts`, `timestamp`. The last 5 frames per ANPR camera are kept as a fallback for a missing fleet snapshot.
  - `reset_session()`: stops threads and clears state.
- **`stability.py`**: `ScaleStabilityMachine` (singleton `scale_state_machine`). States `SCALE_IDLE`, `SCALE_STABILIZING`, `SCALE_STABLE_RECORDED`. `process_new_weight`, `set_network_status`, `abort_offline_session`, `_trigger_upload`, `_transmit_online_weighment`. Calls `record_unsent_weighment()` when it drops a weighment.
- **`telemetry.py`**: in-memory store. Event log (last 20), latest weighment, error counts, unsent-weighment counter. `record_system_event`, `record_weighment_result`, `record_error_event`, `record_unsent_weighment`, `get_*`, `reset_telemetry`.
- **`db.py`**: `init_db()` sets WAL and creates `wifi_networks`.
- **`wifi_vault.py`**: save, list (no passwords), get, delete and clear saved networks.
- **`logger.py`**: `setup_colored_logging`.

## `src/devices/`

- **`scale.py`**: `ScaleUARTReader` (singleton via `get_uart_reader()`): `start`, `stop`, `restart`, `is_alive`. Packets end at CR, LF, STX, ETX, 256 bytes, or 300 ms of silence. Weight is read as `\d{3,6}MN` first, then as any signed number.
- **`camera.py`**: `fetch_image_bytes(url)` (HTTP GET, or one OpenCV RTSP frame encoded at JPEG 85), `capture_anpr_snapshots()` (1-based indexes), `capture_all_camera_snapshots()` (labels `anpr_N`, `aux_N`), `log_camera_fleet()`. All logging masks `user:pass@`. TLS verification is off for HTTP snapshots because LAN cameras use self-signed certificates.
- **`led/`**: `colors.py`, `driver.py` (GPIO or mock), `controller.py` (`led_controller`: `set_idle`, `set_active`, `set_network_status`, `trigger_cloud_success`, `startup_test`, `cleanup`).
- **`wifi/`** (package):

| File | Role |
| :--- | :--- |
| `runner.py` | `run_nmcli` (locked, `sudo -n` when not root), `get_wifi_interface`, simulation mode |
| `activity.py` | `nmcli_lock`, `suspend_watchdog`, `is_watchdog_suspended` |
| `connectivity.py` | `is_network_connected` (TCP to 1.1.1.1:53, 8.8.8.8:53) |
| `watchdog.py` | `WiFiWatchdog` thread, `notify_network_status`, start, stop, `is_watchdog_running` |
| `hotspot.py` | `start_hotspot`, `stop_hotspot`, `start_emergency_hotspot`, `stop_emergency_hotspot`, `is_hotspot_active` |
| `connection.py` | `connect_wifi`, `connect_to_wifi`, `get_active_wifi_ssid`, `get_existing_profile` |
| `scanner.py` | `scan_networks`, `get_available_networks` |
| `ip.py`, `constants.py` | Gateway lookup; SSID `hermes`, `10.42.0.1`, ports 80 and 5354 |
| `portal_service.py` | `PortalService` starts and stops DNS and HTTP portal |
| `portal_http.py`, `portal_handlers.py` | HTTP server and handler (`/connect`, `/networks`, `/status`, probes, `/.well-known/captive-portal`) |
| `portal_dns.py` | UDP DNS responder |
| `portal_redirect.py` | iptables redirects, stale-listener cleanup |
| `portal_capport.py` | NetworkManager dnsmasq file (wildcard DNS, DHCP option 114) |
| `portal_hosts.py` | `/etc/hosts` entries for `hermes.local`, `hermes.config` |
| `ui/index.html` | Portal page |

## `src/integrations/`

- **`anpr.py`**: `send_frame_to_anpr_server` returns `(plate, status)`; `dispatch_anpr_batch` and `send_and_record_anpr_frame` run it in a pool; `get_highest_frequency_plate` votes; `resolve_anpr_endpoint` maps `0.0.0.0` to `127.0.0.1` and appends `/recognize`. Reads `results[0].plate` from Argus responses, or flat keys (`plate`, `number_plate`, `plate_number`, `text`, `result`).
- **`gluvok.py`**: `post_to_cloud(package)` builds the image list and calls `transmit_entry_multipart(...)`, which returns `(ok, entry_id, error, timed_out)`. Retries 429/5xx/timeouts up to 3 times with one `Idempotency-Key`; sends at most 3 images. Plates that are empty or placeholders (`UNKNOWN`, `NONE`, `NULL`, `SUCCESS`, ...) are sent as `NO_PLATE_DETECTED`.

## `src/services/image_compressor.py`

`compress_image_bytes(bytes, max_dim=1920, quality=75)`: downscale, then JPEG at quality 75 with optimization. Returns the input on decode or encode failure.

## `src/web/`

Files: `app.py` (`create_app`, security headers, error handlers), `server.py` (`FallbackWebServer`, host `0.0.0.0`, port 8080), `auth.py`, `validation.py`, `blueprints/api.py`, `blueprints/views.py`, `templates/index.html` (dashboard), `templates/wifi.html`, `static/` (Tailwind and Lucide bundles).

### REST API (`/api`)

| Method and path | Auth | Purpose |
| :--- | :--- | :--- |
| `POST /login` | No (rate limited) | `{userid, password}` returns `{token}` |
| `POST /logout` | No | Revokes the presented token |
| `GET /status` | Optional | Health for anyone; full detail with a token |
| `GET /config`, `POST /config` | Token | Read, or validate and save runtime settings; restarts UART if port or baud changed. Fields in `IMMUTABLE_FIELDS` are rejected. |
| `GET /networks`, `GET /wifi/scan` | No | Scan nearby networks |
| `GET /wifi/saved` | Token | Saved SSIDs |
| `DELETE /wifi/saved/<ssid>` | Token | Remove a saved network |
| `POST /wifi` | Token | Save and connect `{ssid, password}` |
| `POST /wifi/clear` | Token | Clear saved credentials and vault |

`GET /api/status` fields: `status`, `scale{state,current_weight}`, `argus{online}` (cached 5 s), `cloud{configured,unsent_weighments}`, `wifi{connected,hotspot_active}`. With a token it adds `cloud.center_id`, `wifi.ssid`, `config`, `latest_weighment`, `error_counts`, `events`.

### Pages and probes (`views.py`)

`/`, `/index`, `/scale`, `/anpr`, `/cloud`, `/wifi`, `/telemetry`, `/errors`, `/config`, `/admin` all serve `index.html`. `/wifi_portal`, `/networks`, the OS probe URLs (`/generate_204`, `/hotspot-detect.html`, `/canonical.html`, `/ncsi.txt`, `/connecttest.txt`) and `/.well-known/captive-portal` support the captive portal.

### Auth (`auth.py`)

`create_session_token`, `validate_session_token` (2 h sliding), `revoke_session_token`, `is_rate_limited`/`record_failed_login` (per key, 5 per 60 s), `verify_credentials` (constant time), `require_runtime_secrets`, `auth_required`.

### Validation (`validation.py`)

`validate_config_payload`: serial port pattern, baud list (300 to 115200), camera URL scheme and characters, `stability_duration` 1 to 60 s, `stability_tolerance` 0.1 to 50 kg.

## Scripts

- `build.py`: Nuitka build of `main.py` and `src/` into `dist/hermes` (or `--output-dir`); `--run` launches it.
- `deploy.py`: see ARCHITECTURE section 6. Builds the systemd unit, sudoers file and provisioning script.
- `keygen.py`: `generate_client_license(...)` writes a signed `data/client.lic`.
- `package.py`: builds a release tarball.

## Tests

`uv run pytest`. Files by area:

- Scale and session: `test_scale_uart`, `test_session_fallback`, `test_thread_supervision`, `test_threading_isolation`, `test_online_transmission`
- ANPR and cloud: `test_anpr_async`, `test_anpr_client`, `test_anpr_status_counts`, `test_cloud_post`, `test_camera`, `test_image_compressor`
- Web: `test_web_server`, `test_auth_rate_limit`, `test_logout`, `test_security_headers`, `test_validation`
- Wi-Fi: `test_wifi_manager`, `test_wifi_hotspot`, `test_wifi_portal`, `test_wifi_capport`, `test_wifi_vault`
- Other: `test_credentials` (no credential literals outside `tests/`, secrets required), `test_deploy_unit`, `test_license`, `test_logger`, `test_rgb_led`

Before committing, run `uv run ruff check --fix`, `uv run ty check` and `uv run pytest`.
