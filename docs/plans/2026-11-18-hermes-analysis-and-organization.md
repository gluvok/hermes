# Hermes Analysis and Organization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Conduct an exhaustive diagnostic audit of the Hermes edge weighbridge controller to uncover every architectural contradiction, hardware leakage, security hazard, and concurrency defect, then systematically consolidate and refactor the system into a resilient edge appliance using Scrum-ban sprints with an ECC final verification and version conflict audit.

**Architecture:** Apply a 6-phase Scrum-ban agile framework: Phase 1 conducts root-cause static and dynamic diagnostic audits across 5 critical dimensions; Phase 2 builds a pure-software test sandbox eliminating host/hardware leaks; Phase 3 consolidates the 17-file Wi-Fi package into 3 cohesive modules adhering to YAGNI and Python idioms; Phase 4 replaces destructive "offline discard" with SQLite store-and-forward queueing; Phase 5 eliminates hardcoded credentials; Phase 6 executes the Everything Claude Code (ECC) final verification gate with exhaustive version conflict resolution.

**Tech Stack:** Python 3.14, uv, pytest, ruff, ty, SQLite 3 (WAL mode), Flask 3.1, OpenCV (cv2), pyserial, python-periphery.

---

## Skill Map & Methodological Alignment

| Flaw Category / Phase | Target Subsystem | Primary Skill | Supporting Skills |
| :--- | :--- | :--- | :--- |
| **Plan Orchestration** | Entire repository | `@skills/writing-plans` | `@skills/executing-plans`, `@skills/kaizen` |
| **Hardware Isolation Audit** | Serial UART, GPIO, nmcli | `@skills/systematic-debugging` | `@skills/code-review-checklist`, `@skills/test-driven-development` |
| **Security & Secrets Audit** | `client_config.py`, db, auth | `@skills/security-audit` | `@skills/find-bugs`, `@skills/clean-code` |
| **Architecture Audit & YAGNI** | `src/devices/wifi/` (17 files) | `@skills/architecture` | `@skills/ponytail`, `@skills/clean-code` |
| **Concurrency & RTSP Leaks** | `session.py`, `camera.py` | `@skills/performance-profiling` | `@skills/systematic-debugging` |
| **Data Durability & Store-Forward** | `stability.py`, `db.py` | `@skills/architecture` | `@skills/test-driven-development`, `@skills/clean-code` |
| **ECC Final Audit & Version Conflicts**| Full repository & package metadata | `@skills/verification-loop` | `@skills/security-review`, `@skills/clean-code`, `@skills/benchmark` |

---

## Baseline Discovery & Existing Flaw Inventory

1. **Host & Subprocess Leaks in Tests**: Running `pytest` triggers real `sudo -n` commands from `portal_capport.py` and `portal_redirect.py` (prompting `Password:` in terminal), while `test_web_server.py` triggers `get_uart_reader().restart()` which spawns a background thread attempting to open `/dev/ttyAMA0` and leaking error loops.
2. **Artificial Micro-File Fragmentation**: Blindly adhering to an artificial "60 lines per file" rule fragmented `src/devices/wifi/` into 17 tiny files (20-60 lines each), forcing compressed single-line semicolon syntax (`a(); b(); return c;`), lazy circular imports, and global state across multiple files (`SIMULATION_STATE`, `_hotspot_active`).
3. **Architectural Contradiction & Silent Data Loss**: `ARCHITECTURE.md` promises "Write-Ahead SQLite Local Durability... guaranteeing zero data loss", yet `src/core/stability.py:160-168` discards truck weighments and camera captures whenever Wi-Fi is temporarily disconnected.
4. **Hardcoded Secrets in Source Control**: `src/config/client_config.py` hardcodes live RTSP credentials (`admin:Poly%40123`, `admin:Cctv%40222`), Wi-Fi passwords, and device keys in plain text tracked by git.
5. **RTSP Reconnection Thrashing**: `camera.py:_fetch_rtsp_frame()` creates a new `cv2.VideoCapture` instance and tears it down on every single frame grab (called every 1s during active weighing), causing CPU spikes, network reconnection latency, and FFMPEG socket exhaustion.
6. **Synchronous Startup Delays**: `led_controller.startup_test(delay=1.0)` blocks the main initialization thread for 3 consecutive seconds with raw `time.sleep()`.
7. **Version & Environment Fragility**: `pyproject.toml` pins `requires-python = ">=3.14"`, creating an immediate installation failure on standard Raspberry Pi OS / Debian Bookworm edge devices (which ship with Python 3.11 or 3.12). Additionally, `opencv-python` includes desktop X11 dependencies rather than `opencv-python-headless` for headless edge deployments.

---

## Phase 1: Deep Diagnostic Audit (The Flaw Discovery Sprint)

### Task 1: Audit Hardware Isolation & Subprocess Host Leakage
**Component:** Hardware drivers & host process boundaries (`src/devices/scale.py`, `src/devices/wifi/`, `tests/`)  
**Skills:** `@skills/systematic-debugging`, `@skills/code-review-checklist`

**Files:**
- Audit: `hermes/src/devices/wifi/portal_capport.py:20-35`
- Audit: `hermes/src/devices/wifi/portal_redirect.py:20-30`
- Audit: `hermes/src/devices/wifi/portal_hosts.py:20-30`
- Audit: `hermes/src/devices/scale.py:70-120`
- Audit: `hermes/tests/test_wifi_hotspot.py:25-35`
- Audit: `hermes/tests/test_web_server.py:210-310`

**Step 1: Write diagnostic script to detect unmocked hardware/system calls**
Create `hermes/scripts/diagnose_host_leaks.py` to AST-scan for unmocked `subprocess`, `serial`, and `periphery` calls.

**Step 2: Run diagnostic script**
Run: `cd hermes && uv run python scripts/diagnose_host_leaks.py`  
Expected: Output cataloging all direct calls to `subprocess`, `serial`, and `periphery` in `src/`.

**Step 3: Document root cause for test leakage**
Trace in `tests/test_wifi_hotspot.py` and `tests/test_web_server.py`:
1. `start_emergency_hotspot` calls `setup_nm_capport_config()`, which runs `subprocess.run(["sudo", "-n", ...])`. Root cause: `setup_nm_capport_config` missing from mock patches in `test_wifi_hotspot.py`.
2. `POST /api/config` calls `get_uart_reader().restart()`. Root cause: `ScaleUARTReader` singleton is not mocked in `test_web_server.py`.

**Step 4: Commit diagnostic tool**
```bash
git add hermes/scripts/diagnose_host_leaks.py
git commit -m "chore(audit): add diagnostic script for hardware and host leaks"
```

---

### Task 2: Audit Security Attack Surface & Hardcoded Credentials
**Component:** Secrets management & API authentication (`src/config/client_config.py`, `src/core/db.py`, `src/web/auth.py`)  
**Skills:** `@skills/security-audit`, `@skills/find-bugs`

**Files:**
- Audit: `hermes/src/config/client_config.py:1-28`
- Audit: `hermes/src/core/db.py:43-52`
- Audit: `hermes/src/web/auth.py:13-25`
- Audit: `hermes/src/web/blueprints/api.py:195-240`

**Step 1: Write credential exposure detector**
Create `hermes/scripts/audit_credentials.py` scanning for hardcoded RTSP passwords, device keys, and plaintext SQLite schemas.

**Step 2: Run credential scan**
Run: `cd hermes && uv run python scripts/audit_credentials.py`  
Expected: Flags `client_config.py` RTSP strings, `WIFI_PASSWORD`, `DEVICE_KEY`, and `auth.py` default credentials.

**Step 3: Document findings and remediation path**
1. `src/config/client_config.py` exposes production RTSP camera passwords and Wi-Fi credentials in git history.
2. `src/core/db.py` creates table `wifi_networks` with `password TEXT NOT NULL` without hashing or DPAPI/keychain encryption.
3. Remediation path: Strip secrets to `.env` or encrypted key-value store, mask RTSP credentials in telemetry and logs.

**Step 4: Commit security audit script**
```bash
git add hermes/scripts/audit_credentials.py
git commit -m "chore(audit): add credential and secret exposure scan script"
```

---

### Task 3: Audit Wi-Fi Micro-File Fragmentation & Anti-Patterns
**Component:** Wi-Fi driver & captive portal package (`src/devices/wifi/`)  
**Skills:** `@skills/architecture`, `@skills/ponytail`, `@skills/clean-code`

**Files:**
- Audit: `hermes/src/devices/wifi/` (all 17 files)
- Audit: `hermes/wifi_setup.py:1-59`

**Step 1: Write file metrics analyzer**
Create `hermes/scripts/audit_module_fragmentation.py` to calculate LOC, semicolon density, and lazy imports.

**Step 2: Run module fragmentation analysis**
Run: `cd hermes && uv run python scripts/audit_module_fragmentation.py`  
Expected: Reports on all 17 files confirming extreme fragmentation and compressed single-line semicolon syntax.

**Step 3: Define target consolidation architecture**
Collapse 17 files down to 3 logically cohesive, readable modules:
1. `src/devices/wifi/service.py`: NetworkManager (`nmcli`) connection management, scanning, connectivity status, and hotspot lifecycle.
2. `src/devices/wifi/portal.py`: Captive DNS server, RFC 8910/RFC 8908 DHCP Option 114 endpoints, probe redirects, and web UI handlers.
3. `src/devices/wifi/watchdog.py`: Debounced network health monitor thread, status callbacks, and emergency fallback triggers.

**Step 4: Commit fragmentation audit tool**
```bash
git add hermes/scripts/audit_module_fragmentation.py
git commit -m "chore(audit): add script to analyze Wi-Fi package fragmentation"
```

---

### Task 4: Audit Concurrency, Memory & Video Pipeline Bottlenecks
**Component:** Image capture and thread pooling (`src/devices/camera.py`, `src/core/session.py`)  
**Skills:** `@skills/performance-profiling`, `@skills/systematic-debugging`

**Files:**
- Audit: `hermes/src/devices/camera.py:56-82`
- Audit: `hermes/src/core/session.py:108-130`, `163-205`
- Audit: `hermes/src/integrations/anpr.py:60-110`

**Step 1: Write RTSP connection overhead benchmark**
Create `hermes/scripts/benchmark_camera_overhead.py` to measure `cv2.VideoCapture` lifecycle cost.

**Step 2: Run camera benchmark**
Run: `cd hermes && uv run python scripts/benchmark_camera_overhead.py`  
Expected: Measures base instantiation latency; documents why reconnecting to RTSP every 1 second over network causes 500ms-2000ms latency spikes per frame.

**Step 3: Commit benchmark script**
```bash
git add hermes/scripts/benchmark_camera_overhead.py
git commit -m "chore(audit): add camera pipeline overhead benchmark script"
```

---

## Phase 2: Test Harness Hardening & Safe Sandboxing

### Task 5: Eliminate Hardware & Subprocess Leaks in Unit Tests
**Component:** Unit test suite isolation (`tests/`)  
**Skills:** `@skills/test-driven-development`, `@skills/systematic-debugging`

**Files:**
- Modify: `hermes/tests/test_wifi_hotspot.py`
- Modify: `hermes/tests/test_web_server.py`
- Modify: `hermes/tests/conftest.py`

**Step 1: Create a root `conftest.py` with automatic hardware guards**
Create `hermes/tests/conftest.py` ensuring simulation mode is forced and blocking raw `os.system` / `subprocess` calls.

**Step 2: Patch `setup_nm_capport_config` and `ScaleUARTReader` in tests**
Patch `setup_nm_capport_config` in `test_wifi_hotspot.py` and `get_uart_reader` in `test_web_server.py`.

**Step 3: Run pytest and verify clean execution**
Run: `cd hermes && uv run pytest -s`  
Expected: 128 tests pass with 0 `Password:` prompts and 0 `[Errno 2] could not open port /dev/ttyAMA0` logs.

**Step 4: Commit test isolation fix**
```bash
git add hermes/tests/conftest.py hermes/tests/test_wifi_hotspot.py hermes/tests/test_web_server.py
git commit -m "fix(tests): sandbox hardware calls and eliminate subprocess sudo prompts"
```

---

## Phase 3: Wi-Fi Subsystem Consolidation & Slop Elimination

### Task 6: Consolidate 17 Micro-Files into 3 Cohesive Modules
**Component:** `src/devices/wifi/`  
**Skills:** `@skills/clean-code`, `@skills/ponytail`, `@skills/architecture`

**Files:**
- Create: `hermes/src/devices/wifi/service.py` (Unified NetworkManager interface)
- Create: `hermes/src/devices/wifi/portal.py` (Unified captive portal server & handlers)
- Modify: `hermes/src/devices/wifi/watchdog.py` (Cleaned watchdog thread)
- Modify: `hermes/src/devices/wifi/__init__.py` (Preserved public API exports)
- Delete: 14 fragmented files (`activity.py`, `constants.py`, `ip.py`, `portal_capport.py`, `portal_dns.py`, `portal_handlers.py`, `portal_hosts.py`, `portal_http.py`, `portal_redirect.py`, `portal_service.py`, `runner.py`, `scanner.py`, `connection.py`, `connectivity.py`)
- Remove root duplicate: `hermes/wifi_setup.py`

**Step 1: Implement consolidated `service.py`, `portal.py`, and `watchdog.py`**
Eliminate semicolons, eliminate in-function circular imports, and preserve public function signatures.

**Step 2: Run test suite to verify zero regressions**
Run: `cd hermes && uv run pytest tests/test_wifi*.py`  
Expected: 100% PASS with clean imports and identical external contract.

**Step 3: Delete redundant micro-files and commit**
```bash
git rm hermes/src/devices/wifi/portal_*.py hermes/src/devices/wifi/activity.py hermes/wifi_setup.py
git add hermes/src/devices/wifi/
git commit -m "refactor(wifi): consolidate 17 fragmented micro-files into cohesive service and portal modules"
```

---

## Phase 4: Core Engine Alignment & Offline Data Durability

### Task 7: Replace "Offline Discard" with SQLite Store-and-Forward Queue
**Component:** Core stability state machine & SQLite storage (`src/core/stability.py`, `src/core/db.py`)  
**Skills:** `@skills/architecture`, `@skills/test-driven-development`

**Files:**
- Modify: `hermes/src/core/db.py`
- Modify: `hermes/src/core/stability.py:154-180`
- Create: `hermes/src/core/spool.py` (FIFO persistent queue dispatcher)
- Test: `hermes/tests/test_spool_queue.py`

**Step 1: Write failing test for offline weighment spooling**
Create `hermes/tests/test_spool_queue.py` asserting that offline weighments are queued to SQLite, never discarded.

**Step 2: Implement SQLite queue table and spool worker in `src/core/spool.py`**
Create `weighment_queue` table in `src/core/db.py` and implement queue worker that transmits spooled weighments once network status is restored.

**Step 3: Run test to verify it passes**
Run: `cd hermes && uv run pytest hermes/tests/test_spool_queue.py`  
Expected: PASS.

**Step 4: Commit offline durability implementation**
```bash
git add hermes/src/core/db.py hermes/src/core/stability.py hermes/src/core/spool.py hermes/tests/test_spool_queue.py
git commit -m "feat(core): implement SQLite store-and-forward queue to eliminate offline data discard"
```

---

## Phase 5: Configuration Sanitization & Secret Management

### Task 8: Extract Hardcoded Secrets and Sanitize Camera RTSP Credentials
**Component:** System configuration (`src/config/client_config.py`, `.env.example`, `scripts/deploy.py`)  
**Skills:** `@skills/security-audit`, `@skills/clean-code`

**Files:**
- Modify: `hermes/src/config/client_config.py`
- Create: `hermes/.env.example`
- Modify: `hermes/scripts/deploy.py`

**Step 1: Replace hardcoded production credentials with safe development defaults**
Sanitize `hermes/src/config/client_config.py`: replace real RTSP IPs/passwords and device keys with placeholders.

**Step 2: Create `.env.example`**
Document all environment overrides for device IDs, passwords, and URLs.

**Step 3: Fix destructive `deploy.py` script**
Remove the catastrophic `find {target} -name '*.py' -delete` line.

**Step 4: Commit sanitized configuration**
```bash
git add hermes/src/config/client_config.py hermes/.env.example hermes/scripts/deploy.py
git commit -m "security(config): sanitize hardcoded credentials and fix destructive deployment script"
```

---

## Phase 6: ECC Final Verification & Version Conflict Audit

### Task 9: Comprehensive ECC Quality Gate & Dependency Compatibility Audit
**Component:** Complete build, package dependencies, and Python target compatibility  
**Skills:** `@skills/verification-loop`, `@skills/security-review`, `@skills/clean-code`, `@skills/benchmark`

**Files:**
- Audit & Modify: `hermes/pyproject.toml`
- Audit & Modify: `hermes/.python-version`
- Audit & Modify: `hermes/.github/workflows/release.yml`
- Test: Full validation pipeline

**Step 1: Check and resolve Python version conflicts**

- Current setting in `pyproject.toml`: `requires-python = ">=3.14"`.
- Target environment: Raspberry Pi OS (Debian 12 Bookworm default is Python 3.11/3.12). Pinned `>=3.14` guarantees installation failure on standard production Pis.
- Update `pyproject.toml` to: `requires-python = ">=3.11"`.
- Ensure code adheres to Python 3.11+ backward compatibility (using standard `from __future__ import annotations`).

**Step 2: Audit dependency graph for version conflicts**

Run:
```bash
cd hermes
# Verify exact dependency lockfile resolution with zero drift
uv lock --check
# Verify zero installed package dependency conflicts
uv pip check
```
Expected output:
- `Resolved packages in ...ms` (lockfile valid)
- `All installed packages are compatible` (0 dependency conflicts)

**Step 3: Verify OpenCV package variant for headless edge**

- Check if `opencv-python` (with desktop X11 GUI dependencies) should be paired with `opencv-python-headless` for headless edge environments.
- In `pyproject.toml`, document headless option or fallback.

**Step 4: Run ECC 5-Phase Verification Loop**

Execute the complete verification chain:
```bash
cd hermes
# 1. Type check
uv run ty check
# 2. Code style & lint check
uv run ruff check .
# 3. Unit test suite with coverage
uv run pytest -v
# 4. Git repository hygiene check
git status --porcelain
```
Expected output:
- Type checker: 0 errors
- Ruff: All checks passed
- Pytest: 100% pass, 0 leaked threads, 0 subprocess sudo prompts
- Git: Clean working tree

**Step 5: Commit final version reconciliation and verification audit**

```bash
git add hermes/pyproject.toml hermes/.python-version hermes/.github/workflows/release.yml hermes/uv.lock
git commit -m "chore(release): resolve Python version compatibility and complete ECC verification audit"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-11-18-hermes-analysis-and-organization.md`. Two execution options:

1. **Subagent-Driven (this session)** - Dispatch fresh subagents per task, review diffs between tasks, rapid iterative execution.
2. **Parallel Session (separate)** - Open a new session with `executing-plans`, batch execution with systematic checkpoints.

Which approach do you prefer?
