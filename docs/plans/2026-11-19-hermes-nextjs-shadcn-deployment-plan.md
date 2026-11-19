# Hermes Next.js + shadcn/ui Migration & Graceful Edge Deployment Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modernize Hermes edge console from vanilla HTML to a Next.js 16 + shadcn/ui architecture (reusing Janus's design tokens and OKLCH color palette), integrate official shadcn skills via `skills.sh` with full component documentation in `docs/shadcn/`, and implement a zero-data-loss RS232 SIGTERM drain protocol for containerized Raspberry Pi updates via Watchtower and GitHub Actions.

**Architecture:** The Raspberry Pi edge console runs Hermes and Argus with a continuous RS232 UART reader and FastAPI inference engine. The edge dashboard is migrated to a Next.js + shadcn/ui frontend built via GitHub Actions and served locally on `hermes.local`. Container updates via Watchtower are safeguarded by a dedicated SIGTERM drain trap that guarantees in-flight serial weighments and SQLite database transactions are completed before container termination.

**Tech Stack:**
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui (Radix primitives, Lucide icons), OKLCH theme tokens aligned with Janus.
- **Backend Edge Engine:** Python 3.14, Flask/FastAPI REST API, SQLite WAL, PySerial UART multithreading.
- **Deployment & Edge Orchestration:** Docker Compose, Watchtower auto-updater, GitHub Actions CI/CD (`linux/arm64`), Caddy SSL reverse proxy (Phase 2), Monorepo unification & Rust engine migration (Phase 3).

---

## Scope Division: Now vs Later

### 🟢 Phase 1: Immediate Scope (NOW)
1. **Shadcn Skill Installation (`skills.sh`) & Component Docs Directory:**
   - Install official `shadcn/ui` skill into `hermes/.agents/skills/` via `skills.sh`.
   - Create `docs/shadcn/` and maintain markdown documentation for each shadcn component.
2. **Graceful Container Shutdown Protocol & RS232 Drain Handler:**
   - Implement SIGTERM/SIGINT signal trapping in Hermes core engine.
   - Drain protocol: allow in-flight stability checks and SQLite writes to flush, close serial port, exit with code 0 within Docker `stop_grace_period: 30s`.
3. **Minimal Watchtower & Release Pull Provisioning Scripts for Raspberry Pi:**
   - Production Docker Compose configuration with volume mounts, environment secrets, and Watchtower update labels.
   - Minimal release provisioning script (`scripts/deploy_pi.sh`) for automated deployment.
   - GitHub Actions workflow (`.github/workflows/release-edge.yml`) for multi-arch container image publishing.
4. **Next.js + shadcn/ui Edge Frontend Scaffold & Build Workflow:**
   - Scaffold Next.js application in `hermes/src/web/frontend/` matching Janus tokens and API client.
   - Configure GitHub Actions build workflow (`.github/workflows/build-frontend.yml`) for headless artifact packaging.
5. **Kiosk Dual-Console UI Migration to shadcn Components:**
   - Migrate Operator Kiosk HUD (live scale weight, camera preview, verified plate badge, contextual actions) and Developer Console (subsystem tabs) into shadcn components.
   - Generate component documentation markdown files in `docs/shadcn/`.
6. **Holistic Multi-Repo Verification Gate:**
   - Run complete test suites across Hermes (165+ tests), Argus (200 tests), Janus (569 tests), and linting audits.

### 🟡 Phase 2 & 3: Staged Future Iterations (LATER)
1. **Caddy Reverse Proxy & Global SSL (`raspberrypi.local` anywhere):**
   - Configure automated Let's Encrypt / Tailscale / Cloudflare Tunnel Caddy ingress once containerized deployment on Pi stabilizes.
2. **Hermes + Argus Monorepo Unification:**
   - Consolidate both repositories into a single tightly-coupled monorepo with shared types and atomic release management.
3. **Rust Engine Migration:**
   - Incrementally rewrite the RS232 serial stream parser and camera dispatch pipeline in Rust for ultra-low latency and zero-copy ring buffering.

---

## Detailed Implementation Tasks

### Task 1: Install shadcn/ui Skill via `skills.sh` & Establish Component Documentation Directory

**Dedicated Skill:** `@writing-skills` / `@shadcn`

**Files:**
- Modify: `hermes/skills-lock.json`
- Create: `hermes/.agents/skills/shadcn/SKILL.md`
- Create: `hermes/docs/shadcn/README.md`
- Create: `hermes/docs/shadcn/card.md`
- Create: `hermes/docs/shadcn/badge.md`
- Create: `hermes/docs/shadcn/button.md`
- Create: `hermes/docs/shadcn/tabs.md`
- Create: `hermes/docs/shadcn/slider.md`
- Create: `hermes/docs/shadcn/dialog.md`
- Test: `hermes/tests/test_shadcn_docs.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_shadcn_docs.py`:
```python
import os
import unittest
from pathlib import Path

class TestShadcnDocsAndSkill(unittest.TestCase):
    def test_shadcn_skill_and_docs_structure(self):
        root = Path(__file__).parent.parent
        
        # Verify shadcn skill exists in skills-lock and directory
        skill_file = root / ".agents" / "skills" / "shadcn" / "SKILL.md"
        self.assertTrue(skill_file.exists(), f"Missing {skill_file}")
        
        # Verify docs/shadcn directory exists
        docs_dir = root / "docs" / "shadcn"
        self.assertTrue(docs_dir.is_dir(), f"Missing {docs_dir}")
        self.assertTrue((docs_dir / "README.md").exists())
        
        # Verify core component docs exist
        required_components = ["card", "badge", "button", "tabs", "slider", "dialog"]
        for comp in required_components:
            doc_file = docs_dir / f"{comp}.md"
            self.assertTrue(doc_file.exists(), f"Missing doc for component: {comp}")
            content = doc_file.read_text()
            self.assertIn(f"# {comp.capitalize()}", content)
            self.assertIn("## Usage", content)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_docs.py -v`
Expected: FAIL with missing files.

**Step 3: Implement minimal code**

1. Install shadcn skill and register in `skills-lock.json`:
   Add entry to `skills-lock.json` pointing to official `shadcn/ui` skill.
2. Create `hermes/.agents/skills/shadcn/SKILL.md` containing the procedural rules for shadcn CLI, component composition, and OKLCH theming.
3. Create `hermes/docs/shadcn/README.md` explaining the component registry convention and component usage.
4. Create the 6 markdown reference files (`card.md`, `badge.md`, `button.md`, `tabs.md`, `slider.md`, `dialog.md`) documenting component props, imports, and Janus OKLCH design token mapping.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_docs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/tests/test_shadcn_docs.py hermes/skills-lock.json hermes/.agents/skills/shadcn hermes/docs/shadcn
git commit -m "feat(shadcn): install shadcn skill from skills.sh and scaffold component documentation"
```

---

### Task 2: Implement Zero-Data-Loss SIGTERM RS232 Drain Protocol in Hermes

**Dedicated Skill:** `@backend-architect`

**Files:**
- Create: `hermes/src/core/shutdown.py`
- Modify: `hermes/src/core/engine.py` (or main loop runner)
- Test: `hermes/tests/test_shutdown_drain.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_shutdown_drain.py`:
```python
import time
import signal
import threading
import unittest
from unittest.mock import MagicMock
from src.core.shutdown import GracefulShutdownDrain

class TestShutdownDrain(unittest.TestCase):
    def test_drain_handler_waits_for_inflight_session(self):
        drain = GracefulShutdownDrain(grace_period=2.0)
        self.assertFalse(drain.is_shutting_down)

        # Simulate active weighment session
        drain.begin_session("sess-123")
        self.assertTrue(drain.has_active_session)

        # Trigger shutdown signal
        drain.request_shutdown(signum=signal.SIGTERM)
        self.assertTrue(drain.is_shutting_down)

        # In-flight session completes after 0.2s
        def complete_later():
            time.sleep(0.2)
            drain.end_session("sess-123")

        t = threading.Thread(target=complete_later)
        t.start()

        completed = drain.wait_for_drain()
        t.join()
        self.assertTrue(completed)
        self.assertFalse(drain.has_active_session)

    def test_drain_handler_closes_serial_handle_cleanly(self):
        drain = GracefulShutdownDrain(grace_period=1.0)
        mock_serial = MagicMock()
        drain.register_cleanup_hook("serial_port", mock_serial.close)

        drain.request_shutdown(signum=signal.SIGINT)
        drain.wait_for_drain()

        mock_serial.close.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shutdown_drain.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.shutdown'`

**Step 3: Implement minimal code**

Create `hermes/src/core/shutdown.py`:
- Implements `GracefulShutdownDrain`:
  - Registers OS signal listeners for `SIGTERM` and `SIGINT`.
  - Tracks active weighment sessions and SQLite write locks with thread-safe counters.
  - Implements `wait_for_drain(timeout)`: waits until active sessions reach 0, executes registered cleanup hooks (flushing SQLite WAL, closing serial port, persisting offline queue state), and logs a clean exit event.
- Integrates `GracefulShutdownDrain` into the Hermes main engine loop so RS232 continuous streaming stops gracefully without truncated weighment payloads.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shutdown_drain.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/core/shutdown.py hermes/tests/test_shutdown_drain.py
git commit -m "feat(core): implement graceful SIGTERM RS232 drain protocol for zero-data-loss updates"
```

---

### Task 3: Watchtower & Release Pull Provisioning Scripts for Raspberry Pi

**Dedicated Skill:** `@cloud-devops`

**Files:**
- Create: `hermes/deploy/docker-compose.prod.yml`
- Create: `hermes/deploy/deploy_pi.sh`
- Create: `hermes/.github/workflows/release-edge.yml`
- Test: `hermes/tests/test_deploy_config.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_deploy_config.py`:
```python
import unittest
from pathlib import Path
import yaml

class TestDeployConfig(unittest.TestCase):
    def test_production_docker_compose_configuration(self):
        root = Path(__file__).parent.parent
        compose_file = root / "deploy" / "docker-compose.prod.yml"
        self.assertTrue(compose_file.exists(), "Missing docker-compose.prod.yml")
        
        with open(compose_file) as f:
            cfg = yaml.safe_load(f)

        services = cfg.get("services", {})
        self.assertIn("hermes", services)
        self.assertIn("argus", services)
        self.assertIn("watchtower", services)

        # Hermes must have stop_grace_period >= 30s for safe RS232 draining
        hermes_svc = services["hermes"]
        self.assertEqual(hermes_svc.get("stop_grace_period"), "30s")

        # Serial device mapping for Raspberry Pi UART
        self.assertIn("/dev/ttyAMA0:/dev/ttyAMA0", hermes_svc.get("devices", []))

        # Watchtower auto-updater configuration
        wt = services["watchtower"]
        self.assertIn("WATCHTOWER_CLEANUP=true", wt.get("environment", []))
        self.assertIn("WATCHTOWER_INCLUDE_STOPPED=true", wt.get("environment", []))

    def test_deploy_script_syntax(self):
        root = Path(__file__).parent.parent
        deploy_sh = root / "deploy" / "deploy_pi.sh"
        self.assertTrue(deploy_sh.exists(), "Missing deploy_pi.sh")
        content = deploy_sh.read_text()
        self.assertIn("#!/usr/bin/env bash", content)
        self.assertIn("docker compose -f", content)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_deploy_config.py -v`
Expected: FAIL with missing deployment files.

**Step 3: Implement minimal code**

1. Create `hermes/deploy/docker-compose.prod.yml`:
   - Configures `hermes` and `argus` with:
     - `stop_grace_period: 30s` (crucial for RS232 drain).
     - Serial device `/dev/ttyAMA0`.
     - Data volume mounts for `/data` (SQLite WAL) and `/etc/hermes/vault.key`.
     - Watchtower label: `com.centurylinklabs.watchtower.enable: "true"`.
   - Configures `watchtower` container monitoring release image tags every 300 seconds.
2. Create `hermes/deploy/deploy_pi.sh`:
   - Creates required host directories (`/var/lib/hermes/data`, `/etc/hermes`).
   - Ensures correct UART serial permissions (`dialout` group).
   - Runs `docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d`.
3. Create `hermes/.github/workflows/release-edge.yml`:
   - Builds and publishes multi-arch `linux/arm64` and `linux/amd64` Docker images to GitHub Container Registry (GHCR) when a release tag is pushed.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_deploy_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/deploy hermes/.github/workflows/release-edge.yml hermes/tests/test_deploy_config.py
git commit -m "feat(deploy): add production docker-compose with 30s drain period and watchtower auto-update"
```

---

### Task 4: Next.js + shadcn/ui Edge Frontend Scaffold & Build Workflow

**Dedicated Skill:** `@nextjs-app-router-patterns`

**Files:**
- Create: `hermes/src/web/frontend/package.json`
- Create: `hermes/src/web/frontend/tsconfig.json`
- Create: `hermes/src/web/frontend/next.config.mjs`
- Create: `hermes/src/web/frontend/components.json`
- Create: `hermes/src/web/frontend/app/globals.css`
- Create: `hermes/src/web/frontend/lib/api-client.ts`
- Create: `hermes/.github/workflows/build-frontend.yml`
- Test: `hermes/tests/test_frontend_scaffold.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_frontend_scaffold.py`:
```python
import json
import unittest
from pathlib import Path

class TestFrontendScaffold(unittest.TestCase):
    def test_nextjs_frontend_configuration(self):
        root = Path(__file__).parent.parent
        fe_dir = root / "src" / "web" / "frontend"
        
        # Package.json exists and contains Next.js + shadcn dependencies
        pkg_file = fe_dir / "package.json"
        self.assertTrue(pkg_file.exists(), "Missing frontend/package.json")
        with open(pkg_file) as f:
            pkg = json.load(f)
        self.assertIn("next", pkg.get("dependencies", {}))
        self.assertIn("lucide-react", pkg.get("dependencies", {}))

        # components.json exists with Radix + Tailwind setup
        comp_file = fe_dir / "components.json"
        self.assertTrue(comp_file.exists(), "Missing components.json")

        # globals.css contains Janus OKLCH color palette
        css_file = fe_dir / "app" / "globals.css"
        self.assertTrue(css_file.exists())
        css_content = css_file.read_text()
        self.assertIn("oklch(0.145 0.012 155)", css_content)
        self.assertIn("oklch(0.76 0.055 155)", css_content)

        # GitHub workflow for building frontend
        workflow = root / ".github" / "workflows" / "build-frontend.yml"
        self.assertTrue(workflow.exists())
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_frontend_scaffold.py -v`
Expected: FAIL with missing frontend package files.

**Step 3: Implement minimal code**

1. Create `hermes/src/web/frontend/package.json` specifying:
   - `next: "^16.0.0"`, `react: "^19.0.0"`, `@radix-ui/react-*`, `lucide-react`, `tailwindcss: "^4.0.0"`.
   - Scripts: `dev`, `build`, `start`, `lint`.
2. Create `hermes/src/web/frontend/components.json` with standard shadcn configuration (style: default, rsc: true, tailwind v4, path aliases `@/*`).
3. Create `hermes/src/web/frontend/app/globals.css` with exact OKLCH tokens ported from Janus (`--background`, `--card`, `--primary`, `--border`, etc.).
4. Create `hermes/src/web/frontend/lib/api-client.ts` implementing typed fetch methods for `/api/status`, `/api/config`, `/api/login`, and `/api/wifi`.
5. Create `hermes/.github/workflows/build-frontend.yml` running `pnpm install`, `pnpm build`, and verifying clean production output.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_frontend_scaffold.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/frontend hermes/.github/workflows/build-frontend.yml hermes/tests/test_frontend_scaffold.py
git commit -m "feat(frontend): scaffold next.js and shadcn ui setup with janus oklch design tokens"
```

---

### Task 5: Migrate Hermes Kiosk HUD & Developer Console into shadcn Components

**Dedicated Skill:** `@shadcn`

**Files:**
- Create: `hermes/src/web/frontend/components/ui/card.tsx`
- Create: `hermes/src/web/frontend/components/ui/badge.tsx`
- Create: `hermes/src/web/frontend/components/ui/button.tsx`
- Create: `hermes/src/web/frontend/components/ui/tabs.tsx`
- Create: `hermes/src/web/frontend/components/ui/slider.tsx`
- Create: `hermes/src/web/frontend/components/ui/dialog.tsx`
- Create: `hermes/src/web/frontend/components/kiosk/operator-hud.tsx`
- Create: `hermes/src/web/frontend/components/kiosk/developer-console.tsx`
- Create: `hermes/src/web/frontend/components/kiosk/console-mode-switcher.tsx`
- Create: `hermes/src/web/frontend/app/page.tsx`
- Test: `hermes/tests/test_shadcn_components.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_shadcn_components.py`:
```python
import unittest
from pathlib import Path

class TestShadcnComponents(unittest.TestCase):
    def test_shadcn_component_sources_and_docs(self):
        root = Path(__file__).parent.parent
        ui_dir = root / "src" / "web" / "frontend" / "components" / "ui"
        kiosk_dir = root / "src" / "web" / "frontend" / "components" / "kiosk"
        docs_dir = root / "docs" / "shadcn"

        # Verify all UI components exist
        required_ui = ["card.tsx", "badge.tsx", "button.tsx", "tabs.tsx", "slider.tsx", "dialog.tsx"]
        for ui in required_ui:
            self.assertTrue((ui_dir / ui).exists(), f"Missing {ui}")

        # Verify kiosk dual-console components exist
        self.assertTrue((kiosk_dir / "operator-hud.tsx").exists())
        self.assertTrue((kiosk_dir / "developer-console.tsx").exists())
        self.assertTrue((kiosk_dir / "console-mode-switcher.tsx").exists())

        # Verify matching documentation in docs/shadcn/ for each UI component
        for ui in required_ui:
            base_name = ui.replace(".tsx", ".md")
            self.assertTrue((docs_dir / base_name).exists(), f"Missing doc for {base_name}")
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_components.py -v`
Expected: FAIL with missing component files.

**Step 3: Implement minimal code**

1. Create the UI primitives in `src/web/frontend/components/ui/`:
   - `card.tsx`: Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter.
   - `badge.tsx`: Variant badges (`default`, `secondary`, `emerald`, `amber`, `destructive`).
   - `button.tsx`: Variant buttons with standard hover and active transitions.
   - `tabs.tsx`: Accessible Radix tabs list, trigger, and content.
   - `slider.tsx`: Accessible Radix slider with dual-range and step increments for crop tuning.
   - `dialog.tsx`: Radix dialog for superadmin authentication and manual plate editing.
2. Create Kiosk components:
   - `operator-hud.tsx`: The 60/40 hero view with live weight, stability indicator, vehicle framing stage, verified plate badge, and contextual post-weighment micro-actions.
   - `developer-console.tsx`: Subsystem tabs (Scale UART, Cameras & Crop, Cloud Sync, Wi-Fi Network, Telemetry Logs, System Config).
   - `console-mode-switcher.tsx`: Header segmented control toggling between Operator and Developer modes.
3. Update `docs/shadcn/` component documentation with prop definitions and component examples.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_components.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/frontend/components hermes/docs/shadcn hermes/tests/test_shadcn_components.py
git commit -m "feat(ui): migrate operator hud and developer console to shadcn components"
```

---

### Task 6: Holistic Multi-Repo Verification Gate

**Dedicated Skill:** `@verification-loop`

**Files:**
- Test: All suites across Hermes, Argus, and Janus

**Step 1: Run complete Hermes test suite**

Run: `cd /Users/kaalu/importante/hermes && .venv/bin/pytest tests/ -v`
Expected: All 168+ tests PASS without error.

**Step 2: Run Argus test suite**

Run: `cd /Users/kaalu/importante/argus && PYTHONPATH=. .venv/bin/pytest tests/ -q`
Expected: 200 passed.

**Step 3: Run Janus test suite**

Run: `cd /Users/kaalu/importante/janus && npm test`
Expected: 569 passed across 74 test files.

**Step 4: Run static analysis and linting**

Run: `cd /Users/kaalu/importante/hermes && .venv/bin/ruff check .`
Expected: All checks passed!

**Step 5: Validate live Flask + frontend API connectivity**

Run: `/Users/kaalu/importante/hermes/.venv/bin/python -c "from src.web.app import create_app; c = create_app().test_client(); r = c.get('/api/status'); assert r.status_code == 200; print('API verification OK')"`
Expected: `API verification OK`

**Step 6: Summary & Execution Options**

Present the completed verification results and offer subagent vs parallel session execution choices to the user.
