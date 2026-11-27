# Hermes

Weighbridge controller for a Raspberry Pi 5. It reads the scale over UART, captures ANPR and overview camera frames, gets plate readings from the local Argus service, and uploads one entry per weighment to the Gluvok cloud. A Flask console on port 8080 and a fallback hotspot with a captive portal handle diagnostics and Wi-Fi setup.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Module reference: [docs/CODEBASE_REFERENCE.md](docs/CODEBASE_REFERENCE.md).

**Failed uploads are queued.** If an upload fails in a way the cloud may accept later (network error, timeout, 5xx, 429, 401/403), the weighment is stored in SQLite with its `Idempotency-Key` and retried every 30 s until the cloud answers 200 or 201. A weighment discarded while Wi-Fi is offline, rejected with a 400, or arriving at a full outbox is dropped and counted in `cloud.unsent_weighments` on `/api/status`. `cloud.outbox_pending` is the queue size; `cloud.auth_failing` turns true after 3 consecutive 401/403 replies.

## Requirements

- Free-threaded Python 3.14t (`uv sync` installs it from `.python-version`) and [uv](https://docs.astral.sh/uv/)
- Linux with NetworkManager (`nmcli`) for Wi-Fi features

## Run from source

Hermes exits at startup unless both secrets are set:

```bash
export SUPERADMIN_PASS=<console admin password>
export HERMES_HOTSPOT_PASS=<hotspot WPA2 passphrase, 8+ chars>

uv sync
uv run python main.py
```

Cloud credentials come from `data/client.lic`, not from the environment. Without it, the console works but uploads fail.

## Build a native binary

```bash
uv run python scripts/build.py --run   # build and launch
uv run python scripts/build.py         # build into dist/hermes
```

## Deploy to a Pi

Set the two secrets in your local shell, then:

```bash
uv run python scripts/deploy.py --host <user>@<pi-host> \
    --device-id <DEVICE_ID> --device-key <DEVICE_KEY> --center-id <N> --min-weight 70.0
```

The device flags sign a new `data/client.lic`. If you already have one, pass only `--host`.

The script syncs the code to `/opt/hermes`, builds the binary on the Pi, deletes all `.py` files there, writes `data/hermes.env` from your local secrets, creates the `hermes` system user with a sudoers drop-in, and installs and starts the `hermes` systemd service.

**Not yet tested on a Pi:** running as the `hermes` user with the sudoers drop-in. Test a deploy on hardware before relying on it.

Service control on the Pi:

```bash
sudo systemctl status hermes
sudo systemctl restart hermes
sudo journalctl -u hermes -f
cd /opt/hermes && ./run.sh        # run in the foreground
```

## Console

`http://<pi-ip>:8080`. Sign in as `superadmin` (override with `SUPERADMIN_USER`) with `SUPERADMIN_PASS`.

- Without signing in, `/api/status` shows health only.
- Signed in, you can change the serial port, baud rate, stability window and tolerance, camera URLs, and Wi-Fi.
- Failed logins are limited to 5 per minute per IP. Use the sign-out button or `POST /api/logout` to end a session.

## Wi-Fi fallback

When connectivity checks fail twice in a row, Hermes starts a hotspot named `hermes` (passphrase `HERMES_HOTSPOT_PASS`) and a captive portal at `http://10.42.0.1` (`http://hermes.local`). Joining a network from the portal requires the admin user ID and password. The hotspot stops when the internet returns. While offline, weighing is blocked.

Command-line alternative from a source checkout (deploy removes it from the Pi): `sudo python3 wifi_setup.py --scan`, or `--connect --ssid <SSID> --password <PWD>`, or `--hotspot`.

## LED

| Color | Meaning |
| :--- | :--- |
| Green | Idle and online |
| Red | Weighment in progress |
| Yellow | Offline |
| Blue | Upload succeeded (10 s) |

GPIO 17 red, 27 green, 22 blue.

## Development

```bash
uv run ruff check --fix && uv run ty check && uv run pytest -q
```

The same checks run in CI and in `.githooks/pre-push`. Git does not run that hook until you enable it once per clone:

```bash
git config core.hooksPath .githooks
```
