# Hermes — Weighbridge Edge Controller

Industrial weighbridge edge integration controller synchronizing scale serial indicators, multi-camera frame capture, Argus ANPR (Automatic Number Plate Recognition), captive portal Wi-Fi provisioning, local SQLite store-and-forward queue durability, and cloud persistence via the Gluvok API.

---

## Prerequisites

- **Python ≥ 3.14** (configured in `.python-version` and `pyproject.toml`)
- **[uv](https://docs.astral.sh/uv/)** package manager

---

## Getting Started

### 1. Environment Setup

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Install locked project dependencies:

```bash
uv sync
```

### 2. Running Automated Tests

Run the full sandboxed test suite:

```bash
uv run pytest -v
```

All hardware boundaries (`serial`, `subprocess`, camera RTSP network calls) are mocked in `tests/conftest.py`. Tests run without root privileges.

### 3. Running Locally (Development Mode)

Start the edge controller directly with Python:

```bash
uv run python main.py
```

---

## Deployment & Production Operation

### 1. Remote Pi Deployment

Deploy to a target Raspberry Pi via SSH:

```bash
uv run python scripts/deploy.py \
    --host gluvok@hermes.local \
    --device-id pi1 \
    --device-key your_device_key \
    --center-id 1 \
    --min-weight 70.0
```

This command:
1. Generates the Ed25519 digitally signed client license `data/client.lic`.
2. Syncs codebase to `/opt/hermes/` via `rsync`.
3. Installs locked virtual environment via `uv sync`.
4. Compiles binary and runtime launcher into `/opt/hermes/bin/hermes` and `/opt/hermes/run.sh`.
5. Uploads `data/client.lic` to `/opt/hermes/data/client.lic`.
6. Configures and starts the `systemd` service `/etc/systemd/system/hermes.service`.

### 2. Service Management (`systemctl`)

```bash
# Check service status
sudo systemctl status hermes
sudo systemctl status argus

# Stream combined service logs
sudo journalctl -u hermes -u argus -f

# Restart or stop
sudo systemctl restart hermes
sudo systemctl stop hermes
```

---

## Diagnostics Console & Captive Portal

- **Diagnostics UI**: `http://localhost:8080` (or `http://hermes.local:8080`)
- **Emergency Hotspot AP**: `hermes` (WPA Key: `12345678`)
  - Captive Portal: Automatically triggers on connection via RFC 8910 / RFC 8908.
  - Manual access: `http://hermes.local` or `http://10.42.0.1`
  - Automated fallback: Restores AP if network handshake fails.
  - SQLite Wi-Fi Vault: Stores saved networks in `data/hermes.db` for automated reconnection.
- **Standalone Wi-Fi Provisioning CLI**:
  ```bash
  sudo uv run python scripts/wifi_setup.py --scan
  sudo uv run python scripts/wifi_setup.py --connect --ssid <SSID> --password <KEY>
  ```
- **Authentication**: Credentials configured via `SUPERADMIN_USER` and `SUPERADMIN_PASS` environment variables.

---

## Hardware LED Indicators

| Color | State | Description |
| :--- | :--- | :--- |
| 🟢 **Green** | **Idle & Online** | Scale standby at 0.0 kg; connected to Wi-Fi/Internet and ready for vehicle weighing. |
| 🟡 **Yellow** | **Offline** | Disconnected from Wi-Fi; emergency hotspot active. Weighments queued locally. |
| 🔴 **Red** | **Active Weighment** | Vehicle on platform (weight > threshold); weighing and ANPR capture in progress. |
| 🔵 **Blue** | **Cloud Success** | 10-second transient pulse confirming upload to Gluvok Cloud. |
| ⚫ **Off** | **Shutdown** | Daemon stopped; cleanup complete. |

---

For technical specifications, state machines, and concurrency topology, refer to [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
