# Hermes XP + TDD Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the Hermes edge weighbridge controller in a single day using Extreme Programming (XP) and Test-Driven Development (TDD) to eliminate AI slop, consolidate over-fragmented modules, guarantee local SQLite weighment durability, isolate hardware drivers in test harnesses, and sanitize production secrets.

**Architecture:** Adhere strictly to an XP micro-iteration cycle (Red-Green-Refactor). We execute 6 self-contained iterations: Iteration 1 establishes the global pytest sandbox; Iteration 2 consolidates the 17-file Wi-Fi package; Iteration 3 folds single-function service packages and cleans root scripts; Iteration 4 implements SQLite store-and-forward queueing; Iteration 5 sanitizes credentials and deployment scripts; Iteration 6 delivers factual ground-truth documentation and runs the final ECC quality gate.

**Tech Stack:** Python >= 3.14 (free-threaded CPython), uv, pytest, ruff, ty, SQLite 3 (WAL mode), Flask 3.1, OpenCV, pyserial, python-periphery.

---

## Complete Skill Matrix (Mapped by Iteration & Step)

| Iteration / Task | Primary Skills | Step-Level Skills | Purpose & Guardrail |
| :--- | :--- | :--- | :--- |
| **Iteration 1: Test Sandbox** | `@skills/test-driven-development`<br>`@skills/systematic-debugging` | • Step 1: `@skills/test-driven-development`<br>• Step 2: `@skills/systematic-debugging`<br>• Step 3: `@skills/ponytail`, `@skills/python-testing`<br>• Step 4: `@skills/verification-before-completion`<br>• Step 5: `@skills/git-commit-helper` | Eliminate unmocked sudo/serial leaks into macOS host machine during test runs. |
| **Iteration 2: Wi-Fi Consolidation** | `@skills/architecture`<br>`@skills/clean-code`<br>`@skills/deslop` | • Step 1: `@skills/test-driven-development`<br>• Step 2: `@skills/verification-before-completion`<br>• Step 3: `@skills/clean-code`, `@skills/deslop`<br>• Step 4: `@skills/verification-loop`<br>• Step 5: `@skills/ponytail`, `@skills/git-commit-helper` | Collapse 17 micro-files (806 LOC) into 3 modules; eliminate semicolons and circular imports. |
| **Iteration 3: Subsystem Clean-up** | `@skills/clean-code`<br>`@skills/ponytail` | • Step 1: `@skills/python-testing`<br>• Step 2: `@skills/ponytail`, `@skills/deslop`<br>• Step 3: `@skills/verification-before-completion`<br>• Step 4: `@skills/git-commit-helper` | Fold single-function 40-line `image_compressor` into `camera.py`; move `wifi_setup.py` to `scripts/`. |
| **Iteration 4: SQLite Store-Forward** | `@skills/architecture`<br>`@skills/database-design`<br>`@skills/test-driven-development` | • Step 1: `@skills/test-driven-development`<br>• Step 2: `@skills/systematic-debugging`<br>• Step 3: `@skills/database-design`, `@skills/clean-code`<br>• Step 4: `@skills/verification-before-completion`<br>• Step 5: `@skills/git-commit-helper` | Replace destructive "offline discard" with SQLite WAL queue table and FIFO dispatcher. |
| **Iteration 5: Secrets Sanitization** | `@skills/security-audit`<br>`@skills/secrets-management`<br>`@skills/find-bugs` | • Step 1: `@skills/secrets-management`, `@skills/credentials`<br>• Step 2: `@skills/security-review`<br>• Step 3: `@skills/find-bugs`<br>• Step 4: `@skills/systematic-debugging`, `@skills/ponytail`<br>• Step 5: `@skills/git-commit-helper` | Strip hardcoded RTSP credentials from git; eliminate destructive `find ... -delete` in deploy script. |
| **Iteration 6: Ground-Truth Docs & ECC** | `@skills/writing-clearly-and-concisely`<br>`@skills/no-ai-slop`<br>`@skills/verification-loop` | • Step 1: `@skills/writing-clearly-and-concisely`, `@skills/no-ai-slop`<br>• Step 2: `@skills/documentation-templates`<br>• Step 3: `@skills/verification-loop`<br>• Step 4: `@skills/verification-before-completion`<br>• Step 5: `@skills/git-commit-helper` | Rewrite `ARCHITECTURE.md` into factual engineering spec; execute 5-phase ECC verification gate. |

---

## Detailed Task Breakdown (XP Micro-Iterations)

### Iteration 1: Global Test Sandbox & Hardware Decoupling (TDD)

**Files:**
- Create: `hermes/tests/conftest.py`
- Modify: `hermes/tests/test_wifi_hotspot.py`
- Modify: `hermes/tests/test_web_server.py`
- Create: `hermes/tests/test_sandbox_isolation.py`

**Applicable Skills:**
- Primary: `@skills/test-driven-development`, `@skills/systematic-debugging`
- Secondary: `@skills/ponytail`, `@skills/python-testing`, `@skills/verification-before-completion`, `@skills/git-commit-helper`

**Step 1: Write failing test verifying hardware guard isolation**  
*Skill:* `@skills/test-driven-development` (Phase 4.1: Write minimal reproduction test)

Create `hermes/tests/test_sandbox_isolation.py`:
```python
"""Verify tests cannot invoke real subprocess sudo or unmocked serial ports."""

import subprocess
import pytest


def test_unmocked_sudo_is_blocked():
    with pytest.raises(
        RuntimeError, match="Direct system execution blocked in test suite"
    ):
        from tests.conftest import assert_sandbox_active

        assert_sandbox_active()
        subprocess.run(["sudo", "whoami"], check=True)
```

**Step 2: Run test to verify it fails**  
*Skill:* `@skills/systematic-debugging` (Phase 1: Verify reproduction before attempting fix)

Run: `cd hermes && uv run pytest tests/test_sandbox_isolation.py`  
Expected: FAIL (`conftest` not found or sandbox inactive).

**Step 3: Implement global sandbox in `tests/conftest.py` and fix test mocks**  
*Skills:* `@skills/ponytail` (Simplest hook without extra dependencies), `@skills/python-testing`

Create `hermes/tests/conftest.py`:
```python
"""Global pytest fixtures sandboxing hardware, serial, and subprocess execution."""

import subprocess
import pytest

_SANDBOX_ACTIVE = True


def assert_sandbox_active():
    if not _SANDBOX_ACTIVE:
        raise RuntimeError("Sandbox inactive")


@pytest.fixture(autouse=True)
def guard_host_execution(monkeypatch):
    """Enforces simulation state and blocks raw sudo / iptables executions."""
    from src.devices.wifi.runner import SIMULATION_STATE

    SIMULATION_STATE["enabled"] = True

    orig_run = subprocess.run

    def safe_subprocess_run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and any(
            arg in cmd for arg in ["sudo", "iptables", "fuser"]
        ):
            if kwargs.get("check"):
                raise RuntimeError("Direct system execution blocked in test suite")
            return subprocess.CompletedProcess(
                cmd, returncode=0, stdout=b"", stderr=b""
            )
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", safe_subprocess_run)
```

Modify `hermes/tests/test_wifi_hotspot.py` and `hermes/tests/test_web_server.py` to patch `setup_nm_capport_config` and `ScaleUARTReader.restart`.

**Step 4: Run test suite to verify all tests pass without prompts or errors**  
*Skill:* `@skills/verification-before-completion` (Gate: Run full command, inspect exit code and stderr)

Run: `cd hermes && uv run pytest -s`  
Expected: 100% PASS with 0 `Password:` prompts and 0 `[Errno 2]` serial port logs.

**Step 5: Commit Iteration 1**  
*Skill:* `@skills/git-commit-helper` (Conventional commit formatting)

```bash
git add hermes/tests/conftest.py hermes/tests/test_sandbox_isolation.py hermes/tests/test_wifi_hotspot.py hermes/tests/test_web_server.py
git commit -m "fix(test): implement global pytest sandbox preventing host and hardware leaks"
```

---

### Iteration 2: Consolidate Wi-Fi Subsystem (Clean Code, YAGNI & Deslop)

**Files:**
- Create: `hermes/src/devices/wifi/manager.py` (Unified NMCLI connection, scanning, hotspot, watchdog)
- Create: `hermes/src/devices/wifi/portal.py` (Unified captive DNS, HTTP handlers, probe redirects)
- Modify: `hermes/src/devices/wifi/__init__.py` (Public API facade preserving backward compatibility)
- Delete: 14 fragmented files (`activity.py`, `connection.py`, `connectivity.py`, `constants.py`, `hotspot.py`, `ip.py`, `portal_capport.py`, `portal_dns.py`, `portal_handlers.py`, `portal_hosts.py`, `portal_http.py`, `portal_redirect.py`, `portal_service.py`, `runner.py`, `scanner.py`, `watchdog.py`)

**Applicable Skills:**
- Primary: `@skills/architecture`, `@skills/clean-code`, `@skills/deslop`
- Secondary: `@skills/test-driven-development`, `@skills/ponytail`, `@skills/verification-loop`, `@skills/git-commit-helper`

**Step 1: Write integration test covering Wi-Fi public API**  
*Skill:* `@skills/test-driven-development` (Establish contract baseline)

Create `hermes/tests/test_wifi_facade.py`:
```python
"""Verify consolidated Wi-Fi package preserves all public API signatures."""

import unittest
from src.devices.wifi import (
    is_wifi_connected,
    is_network_connected,
    scan_networks,
    connect_to_wifi,
    start_emergency_hotspot,
    stop_emergency_hotspot,
    start_wifi_watchdog,
    stop_wifi_watchdog,
)


class TestWiFiFacade(unittest.TestCase):
    def test_public_interface_exists(self):
        self.assertTrue(callable(is_wifi_connected))
        self.assertTrue(callable(connect_to_wifi))
        self.assertTrue(callable(start_emergency_hotspot))
        self.assertTrue(callable(stop_emergency_hotspot))
```

**Step 2: Run test to verify initial state**  
*Skill:* `@skills/verification-before-completion`

Run: `cd hermes && uv run pytest tests/test_wifi_facade.py`  
Expected: PASS.

**Step 3: Implement consolidated `manager.py`, `portal.py`, and `__init__.py`**  
*Skills:* `@skills/clean-code` (SRP, DRY, max 20 lines functions), `@skills/ponytail` (Boring over clever, fewest files possible), `@skills/deslop` (Remove inline imports, remove compressed semicolon lines)

- Group all NMCLI interaction, interface discovery, scanning, connection state, and watchdog loop into `manager.py`.
- Group all DNS packet interception, HTTP captive portal routes, and RFC 8910 Option 114 endpoints into `portal.py`.
- Remove all semicolon line compression and in-function circular imports.
- Update `src/devices/wifi/__init__.py` to re-export the unified functions.

**Step 4: Run test suite to verify 0 regressions**  
*Skill:* `@skills/verification-loop` (Full test pass verification)

Run: `cd hermes && uv run pytest tests/test_wifi*.py`  
Expected: 100% PASS.

**Step 5: Delete legacy fragmented micro-files and commit**  
*Skills:* `@skills/ponytail` (Deletion over addition), `@skills/git-commit-helper`

```bash
git rm hermes/src/devices/wifi/portal_*.py hermes/src/devices/wifi/activity.py hermes/src/devices/wifi/hotspot.py hermes/src/devices/wifi/runner.py hermes/src/devices/wifi/scanner.py hermes/src/devices/wifi/ip.py hermes/src/devices/wifi/constants.py hermes/src/devices/wifi/connectivity.py hermes/src/devices/wifi/connection.py hermes/src/devices/wifi/watchdog.py
git add hermes/src/devices/wifi/
git commit -m "refactor(wifi): consolidate 17 fragmented micro-files into cohesive manager and portal modules"
```

---

### Iteration 3: Subsystem Clean-up & Script Relocation

**Files:**
- Modify: `hermes/src/devices/camera.py` (Fold `compress_image_bytes` into camera driver)
- Delete: `hermes/src/services/image_compressor.py`, `hermes/src/services/`
- Move: `hermes/wifi_setup.py` -> `hermes/scripts/wifi_setup.py`
- Modify: `hermes/src/core/session.py`, `hermes/src/integrations/gluvok.py` (Update image compression imports)

**Applicable Skills:**
- Primary: `@skills/clean-code`, `@skills/ponytail`
- Secondary: `@skills/deslop`, `@skills/python-testing`, `@skills/verification-before-completion`, `@skills/git-commit-helper`

**Step 1: Write test for camera image compression**  
*Skill:* `@skills/python-testing`

Add test in `hermes/tests/test_camera.py`:
```python
def test_camera_compress_image_bytes():
    from src.devices.camera import compress_image_bytes

    dummy_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    res = compress_image_bytes(dummy_jpeg, max_dim=1920, quality=85)
    assert res is not None or res == dummy_jpeg
```

**Step 2: Fold `compress_image_bytes` into `src/devices/camera.py` and delete `src/services/`**  
*Skills:* `@skills/ponytail` (YAGNI, prune single-function packages), `@skills/deslop`

- Move `compress_image_bytes` directly into `src/devices/camera.py`.
- Update imports in `src/core/session.py` and `src/integrations/gluvok.py`.
- Relocate root `wifi_setup.py` to `scripts/wifi_setup.py`.

**Step 3: Run test suite to verify zero broken imports**  
*Skill:* `@skills/verification-before-completion`

Run: `cd hermes && uv run pytest`  
Expected: 100% PASS.

**Step 4: Commit cleanup**  
*Skill:* `@skills/git-commit-helper`

```bash
git rm -r hermes/src/services hermes/wifi_setup.py
git add hermes/src/devices/camera.py hermes/scripts/wifi_setup.py hermes/src/core/session.py hermes/src/integrations/gluvok.py hermes/tests/test_camera.py
git commit -m "refactor(layout): fold image compressor into camera module and move wifi_setup to scripts"
```

---

### Iteration 4: SQLite Store-and-Forward Weighment Durability (TDD & Database Architecture)

**Files:**
- Modify: `hermes/src/core/db.py`
- Create: `hermes/src/core/spool.py`
- Modify: `hermes/src/core/stability.py:154-180`
- Test: `hermes/tests/test_spool_queue.py`

**Applicable Skills:**
- Primary: `@skills/architecture`, `@skills/database-design`, `@skills/test-driven-development`
- Secondary: `@skills/systematic-debugging`, `@skills/clean-code`, `@skills/verification-before-completion`, `@skills/git-commit-helper`

**Step 1: Write failing test for offline store-and-forward queue**  
*Skill:* `@skills/test-driven-development` (RED phase: Write failing test verifying zero weighment loss)

Create `hermes/tests/test_spool_queue.py`:
```python
"""Verify weighment sessions are spooled to SQLite during network outages and never discarded."""

import json
import unittest
from unittest.mock import patch, MagicMock
from src.core.db import init_db
from src.core.spool import (
    enqueue_weighment,
    get_pending_weighments,
    mark_weighment_completed,
)


class TestSpoolQueue(unittest.TestCase):
    def setUp(self):
        init_db(":memory:")

    def test_weighment_enqueued_and_drained(self):
        payload = {"session_id": "TRUCK_001", "weight": 24500.0, "plate": "DL01AB1234"}
        self.assertTrue(enqueue_weighment("TRUCK_001", payload))
        pending = get_pending_weighments()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["session_id"], "TRUCK_001")
        mark_weighment_completed("TRUCK_001")
        self.assertEqual(len(get_pending_weighments()), 0)
```

**Step 2: Run test to verify it fails**  
*Skill:* `@skills/systematic-debugging` (Verify reproduction before implementation)

Run: `cd hermes && uv run pytest tests/test_spool_queue.py`  
Expected: FAIL (`src.core.spool` does not exist).

**Step 3: Implement `weighment_queue` in `db.py` and spool manager in `spool.py`**  
*Skills:* `@skills/database-design` (WAL mode, FIFO queue indexing, atomic row updates), `@skills/clean-code`

- Add schema to `src/core/db.py`:
```sql
CREATE TABLE IF NOT EXISTS weighment_queue (
    session_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_weighment_queue_status ON weighment_queue(status, created_at);
```
- Implement `src/core/spool.py` with `enqueue_weighment()`, `get_pending_weighments()`, and background queue drain worker.
- Update `src/core/stability.py:_trigger_upload()` to call `enqueue_weighment()` when offline instead of discarding.

**Step 4: Run test to verify it passes**  
*Skill:* `@skills/verification-before-completion` (GREEN phase: Ensure full test suite passes)

Run: `cd hermes && uv run pytest tests/test_spool_queue.py`  
Expected: PASS.

**Step 5: Commit store-and-forward implementation**  
*Skill:* `@skills/git-commit-helper`

```bash
git add hermes/src/core/db.py hermes/src/core/spool.py hermes/src/core/stability.py hermes/tests/test_spool_queue.py
git commit -m "feat(core): implement SQLite store-and-forward queue to eliminate offline data discard"
```

---

### Iteration 5: Secrets Sanitization & Deployment Safety

**Files:**
- Modify: `hermes/src/config/client_config.py`
- Modify: `hermes/src/config/constants.py`
- Modify: `hermes/src/web/auth.py`
- Create: `hermes/.env.example`
- Modify: `hermes/scripts/deploy.py`

**Applicable Skills:**
- Primary: `@skills/security-audit`, `@skills/secrets-management`, `@skills/find-bugs`
- Secondary: `@skills/credentials`, `@skills/systematic-debugging`, `@skills/ponytail`, `@skills/verification-before-completion`, `@skills/git-commit-helper`

**Step 1: Sanitize hardcoded production RTSP passwords and default credentials**  
*Skills:* `@skills/secrets-management`, `@skills/credentials` (Never commit secrets to source control)

- Replace credentials in `src/config/client_config.py` with environment-driven placeholders.
- Remove hardcoded password fallback in `src/web/auth.py`, enforcing an environment variable or randomized session token.
- Update `scripts/deploy.py` to remove `find {target} -name '*.py' -delete`.

**Step 2: Create `.env.example` documenting configuration keys**  
*Skill:* `@skills/security-review` (Audit environment boundary parameters)

Create `hermes/.env.example` with documented keys (`SUPERADMIN_PASS`, `DEVICE_ID`, `DEVICE_KEY`, `CENTER_ID`, `ANPR_CAMERA_URLS`).

**Step 3: Run security scan script to confirm 0 exposed credentials**  
*Skills:* `@skills/find-bugs`, `@skills/verification-before-completion`

Run: `cd hermes && uv run python scripts/audit_credentials.py`  
Expected: 0 production credentials flagged.

**Step 4: Commit sanitization**  
*Skill:* `@skills/git-commit-helper`

```bash
git add hermes/src/config/client_config.py hermes/src/config/constants.py hermes/src/web/auth.py hermes/.env.example hermes/scripts/deploy.py
git commit -m "security(config): sanitize hardcoded credentials and fix destructive deployment script"
```

---

### Iteration 6: Ground-Truth Documentation & ECC Quality Gate

**Files:**
- Rewrite: `hermes/docs/ARCHITECTURE.md`
- Update: `hermes/README.md`
- Update: `hermes/docs/CODEBASE_REFERENCE.md`

**Applicable Skills:**
- Primary: `@skills/writing-clearly-and-concisely`, `@skills/no-ai-slop`, `@skills/verification-loop`
- Secondary: `@skills/documentation-templates`, `@skills/verification-before-completion`, `@skills/git-commit-helper`

**Step 1: Rewrite `ARCHITECTURE.md` into a zero-slop factual specification**  
*Skills:* `@skills/writing-clearly-and-concisely`, `@skills/no-ai-slop` (Zero corporate buzzwords, show don't tell, eliminate colon reveals, factual state machines and thread topologies)

Document:
- Validated state machine flow.
- Consolidated Wi-Fi package architecture.
- SQLite WAL mode store-and-forward durability mechanism.
- Thread topology and free-threaded Python 3.14 safety guarantees.
- Remove all artificial "60 lines per file" claims and offline discard contradictions.

**Step 2: Update `README.md` with operational runbook**  
*Skill:* `@skills/documentation-templates` (Clear runbook and setup guidelines)

Clear instructions for:
- Environment setup: `uv sync`
- Running test suite: `uv run pytest`
- Starting controller: `uv run python main.py`
- Wi-Fi CLI setup: `uv run python scripts/wifi_setup.py`

**Step 3: Run ECC Final Verification Gate**  
*Skill:* `@skills/verification-loop` (Comprehensive 5-Phase verification system)

Run:
```bash
cd hermes
uv lock --check        # Check lockfile drift
uv pip check          # Check dependency conflicts
uv run ty check       # Check type safety
uv run ruff check .   # Check lint
uv run pytest -v      # Run full test suite
git status --porcelain
```
Expected: All checks pass, 0 type errors, 0 lint warnings, 100% tests passing, clean working tree.

**Step 4: Final gate assertion**  
*Skill:* `@skills/verification-before-completion` (No success claims without fresh evidence)

**Step 5: Commit documentation and complete refactoring**  
*Skill:* `@skills/git-commit-helper`

```bash
git add hermes/docs/ARCHITECTURE.md hermes/README.md hermes/docs/CODEBASE_REFERENCE.md
git commit -m "docs: publish ground-truth architecture specification and complete refactoring"
```
