# Hermes Refactoring Design Specification

## Overview & Context
Hermes is an industrial weighbridge controller deployed on Raspberry Pi 5 hardware. It interfaces with an RS-232 serial weighing scale indicator, multi-camera RTSP/HTTP video streams for ANPR license plate OCR, captive portal Wi-Fi provisioning via NetworkManager (`nmcli`), and cloud telemetry persistence via Gluvok API.

This design specification establishes the architectural foundation for refactoring Hermes using **Extreme Programming (XP) + Test-Driven Development (TDD)** within a single-day execution window.

---

## 1. Core Architectural Decisions

| Decision Area | Selected Approach | Rationale |
| :--- | :--- | :--- |
| **Development Lifecycle** | Extreme Programming (XP) + TDD | Rapid, same-day delivery via tight Red-Green-Refactor cycles and continuous test verification. |
| **Python Runtime** | Python `>= 3.14` strictly | Enforces free-threaded CPython (PEP 703) on Raspberry Pi 5 ARM Cortex-A76 cores without GIL bottlenecks. |
| **Subsystem Organization** | Pragmatic 5-Package Structure | Eliminates over-fragmented micro-files while maintaining clean domain boundaries (`core`, `devices`, `integrations`, `web`, `config`). |
| **Wi-Fi Subsystem** | 3-Module Consolidation | Collapses 17 micro-files (806 LOC) into `manager.py`, `portal.py`, and `__init__.py`. Removes semicolon hacks and circular imports. |
| **Data Durability** | SQLite Store-and-Forward Queue | Eliminates the destructive "offline discard" behavior. Weighments and frames are committed to `weighment_queue` in `data/hermes.db` and drained FIFO upon reconnection. |
| **Hardware Isolation** | Global Pytest Sandbox (`conftest.py`) | Intercepts `subprocess`, `serial`, and `periphery` calls across all unit tests to guarantee zero host leakage (`sudo`, serial ports) on macOS and Linux CI. |
| **Documentation** | Ground-Truth Engineering Docs | Replaces speculative fluff in `ARCHITECTURE.md` with factual threading models, state diagrams, and store-and-forward schemas. |

---

## 2. Target Package & Directory Layout

```
hermes/
├── main.py                       # Application bootstrap and clean signal shutdown
├── pyproject.toml                # Pinned dependencies (>=3.14, uv-managed)
├── uv.lock                       # Deterministic dependency lockfile
├── README.md                     # Operational runbook and deployment guide
├── AGENTS.md                     # LLM development rules and coding standards
├── docs/
│   ├── ARCHITECTURE.md           # Ground-truth system architecture & state machines
│   ├── CODEBASE_REFERENCE.md     # Public API interface contracts
│   └── plans/                    # Design specs and atomic execution plans
├── scripts/
│   ├── build.py                  # Nuitka native compilation script
│   ├── deploy.py                 # Remote deployment script (without destructive rm)
│   ├── keygen.py                 # Ed25519 client licensing key generator
│   ├── package.py                # Release tarball packager
│   └── wifi_setup.py             # Relocated standalone Wi-Fi CLI utility
├── tests/
│   ├── conftest.py               # Global test sandbox preventing host leaks
│   ├── test_scale_uart.py        # Serial reader and line buffer framing tests
│   ├── test_camera.py            # HTTP snapshot and RTSP capture tests
│   ├── test_spool_queue.py       # SQLite store-and-forward queue durability tests
│   ├── test_anpr_client.py       # ANPR client and consensus voting tests
│   ├── test_cloud_post.py        # Gluvok API multipart upload tests
│   ├── test_web_server.py        # Diagnostics web console tests
│   ├── test_wifi_manager.py      # Consolidated nmcli Wi-Fi tests
│   └── test_wifi_portal.py       # Captive portal HTTP & DNS tests
└── src/
    ├── config/
    │   ├── __init__.py           # Exports config singleton and ConfigManager
    │   ├── constants.py          # Operational constants, timeouts, buffer sizes
    │   ├── client_config.py      # Client license fallback values (sanitized placeholders)
    │   ├── manager.py            # Thread-safe unified ConfigManager
    │   ├── runtime.py            # In-memory runtime override mutator
    │   ├── store.py              # SQLite storage for runtime config overrides
    │   └── license.py            # Ed25519 license validation
    ├── core/
    │   ├── __init__.py           # Subpackage exports
    │   ├── db.py                 # SQLite initialization (WAL mode, schema migrations)
    │   ├── spool.py              # FIFO store-and-forward weighment queue worker
    │   ├── session.py            # Weighbridge session orchestrator
    │   ├── stability.py          # Weight stabilization state machine
    │   ├── telemetry.py          # In-memory circular event log and metrics store
    │   └── logger.py             # Colored terminal logger
    ├── devices/
    │   ├── __init__.py           # Subpackage exports
    │   ├── scale.py              # RS-232 serial UART driver
    │   ├── camera.py             # IP camera frame grabber and JPEG compression
    │   ├── led.py                # Consolidated RGB LED driver and state controller
    │   └── wifi/                 # Consolidated Wi-Fi package
    │       ├── __init__.py       # Clean public API exports
    │       ├── manager.py        # NetworkManager (nmcli) connection & watchdog
    │       └── portal.py         # Captive portal DNS, HTTP routes, and probe redirects
    ├── integrations/
    │   ├── __init__.py           # Subpackage exports
    │   ├── anpr.py               # Argus ANPR REST client and candidate voting
    │   └── gluvok.py             # Gluvok Cloud API multipart client
    └── web/
        ├── __init__.py           # Subpackage exports
        ├── app.py                # Flask WSGI application factory
        ├── auth.py               # Session token auth and rate limiting
        ├── server.py             # Werkzeug background daemon server runner
        ├── validation.py         # Config input validation
        ├── blueprints/           # Modular route blueprints (api.py, views.py)
        ├── static/               # Bundled assets (Tailwind CSS, Lucide icons)
        └── templates/            # Single-page diagnostic dashboard
```

---

## 3. Data Durability Specification (Store-and-Forward)

```
Scale Stability Confirmed (Stable Weight Recorded)
                    │
                    ▼
     Assemble Complete Weighment Package
   (Weight, Best Plate, Camera Snapshots)
                    │
                    ▼
          Is Network Online?
          ├── YES ──► Attempt Direct Gluvok API Upload
          │               ├── HTTP 200/201 ──► Upload Success (Pulse LED Blue)
          │               └── Network Failure / Timeout
          │                       │
          └── NO ─────────────────┴──► Enqueue to Local SQLite
                                       Table: weighment_queue
                                       Status: 'PENDING'
                                       Payload: Serialized JSON + JPEG Blobs
                                       Transaction: Committed in WAL mode
                                             │
                                             ▼
                                  Background Spool Worker
                                  (Drains FIFO when online)
```

### SQLite Queue Schema
```sql
CREATE TABLE IF NOT EXISTS weighment_queue (
    session_id TEXT PRIMARY KEY,
    weight REAL NOT NULL,
    detected_vehicle_number TEXT NOT NULL,
    camera_snapshots_json TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_weighment_queue_status ON weighment_queue(status, created_at);
```

---

## 4. Test Sandbox & Hardware Decoupling Specification

To prevent real commands (`sudo`, `iptables`, `serial.Serial`) from executing on developer machines or CI runners, `tests/conftest.py` installs interceptors at session startup:
- `subprocess.run`: If arguments include `sudo`, `iptables`, `fuser`, or `tee` outside simulation mode, raises `TestIsolationError`.
- `serial.Serial`: Diverts to in-memory `io.BytesIO` / mock serial stream.
- `periphery.GPIO`: Instantiates mock pin interface without touching `/dev/gpiochip*`.
