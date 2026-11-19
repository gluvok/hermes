# Hermes & Janus Minimalist Unified Dashboard UI Revamp Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Hermes edge dashboard into a professional, minimalist single-view interface matching the exact visual formatting and design tokens of Janus and Argus, providing a clean 2-section hero view for customers/clients with zero debug noise, paired with a non-intrusive slide-over sheet drawer for maintainers.

**Architecture:** 
- **Customer/Client View:** A focused, high-contrast 60/40 hero layout. The left pane renders the live scale indicator with prominent digital weight and stability badge; the right pane renders the camera framing stream with recognized license plate pill and confidence rating. A bottom transaction progression bar displays context-sensitive touch actions ("Zero Scale", "Print Slip", and "Override Plate").
- **Maintainer View:** A slide-over sheet drawer (accessible via subtle header wrench icon or PIN) housing diagnostic tabs (Scale UART, Camera Crop Calibration, Wi-Fi Network & Hotspot, Cloud Spool Queue, Telemetry Logs, System Config) without occluding the client view.
- **Lockstep Parity:** Implemented across both the live edge Flask template (`src/web/templates/index.html` + `static/style.css`) and the Next.js/shadcn App Router application (`src/web/frontend/`) using identical Janus OKLCH design tokens.

**Tech Stack:**
- HTML5 / CSS3 / Tailwind CSS (v4) / OKLCH theme tokens
- Next.js 16 / React 19 / shadcn/ui / Lucide Icons
- Python 3.14 / Flask REST API / PySerial / SQLite WAL

---

## Detailed Implementation Tasks

### Task 1: Refactor Flask Edge Stylesheet (`style.css`) with Janus OKLCH Tokens & Slide-Over Sheet Rules

**Dedicated Skill:** `@ui-ux-pro-max` / `@shadcn`

**Files:**
- Modify: `hermes/src/web/static/style.css`
- Test: `hermes/tests/test_ui_janus_styling.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_ui_janus_styling.py`:
```python
import unittest
from pathlib import Path

class TestUIJanusStyling(unittest.TestCase):
    def test_janus_oklch_tokens_and_sheet_classes(self):
        root = Path(__file__).parent.parent
        css_file = root / "src" / "web" / "static" / "style.css"
        self.assertTrue(css_file.exists(), "Missing static/style.css")
        
        content = css_file.read_text()
        
        # Verify Janus OKLCH background and primary tokens
        self.assertIn("0.145 0.012 155", content, "Missing Janus dark background token")
        self.assertIn("0.76 0.055 155", content, "Missing Janus emerald primary token")
        
        # Verify slide-over maintainer sheet drawer classes
        self.assertIn(".maintainer-sheet", content)
        self.assertIn(".maintainer-sheet-overlay", content)
        self.assertIn(".hero-weight-display", content)
        self.assertIn(".hero-camera-display", content)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_ui_janus_styling.py -v`
Expected: FAIL on missing classes and tokens.

**Step 3: Implement minimal CSS in `style.css`**

Update `hermes/src/web/static/style.css`:
- Define exact Janus OKLCH root variables (`--background: oklch(0.145 0.012 155)`, `--card: oklch(0.185 0.012 155)`, `--primary: oklch(0.76 0.055 155)`, `--border: oklch(0.28 0.015 155)`).
- Style the 60/40 hero container (`.hero-weight-display`, `.hero-camera-display`).
- Implement `.maintainer-sheet` (right: 0, top: 0, width: 480px, max-width: 90vw, transform: translateX(100%), smooth cubic-bezier transition, z-index: 60) and `.maintainer-sheet-overlay` (backdrop blur, fade).

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_ui_janus_styling.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/static/style.css hermes/tests/test_ui_janus_styling.py
git commit -m "feat(ui): add janus oklch tokens and slide-over maintainer sheet styles"
```

---

### Task 2: Redesign Live Flask Template (`index.html`) to Janus Minimalist One-Dash View

**Dedicated Skill:** `@frontend-patterns` / `@clean-code`

**Files:**
- Modify: `hermes/src/web/templates/index.html`
- Test: `hermes/tests/test_web_server.py`

**Step 1: Write the failing test**

Add test assertions to `hermes/tests/test_web_server.py`:
```python
    def test_janus_minimalist_client_view_and_maintainer_sheet(self):
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        
        # Verify client hero elements exist
        self.assertIn('id="client-hero-view"', html)
        self.assertIn('id="live-weight-display"', html)
        self.assertIn('id="vehicle-camera-feed"', html)
        self.assertIn('id="verified-plate-badge"', html)
        self.assertIn('id="action-bar-minimal"', html)
        
        # Verify maintainer sheet exists
        self.assertIn('id="maintainer-sheet"', html)
        self.assertIn('id="btn-open-maintainer-sheet"', html)
        
        # Verify debug clutter is NOT visible in customer view
        self.assertNotIn('SCALE_IDLE', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestWebServer::test_janus_minimalist_client_view_and_maintainer_sheet -v`
Expected: FAIL

**Step 3: Implement minimal code in `index.html`**

Update `hermes/src/web/templates/index.html`:
1. **Header (56px):**
   - Brand logo, "LUVOK Hermes", version badge `v2.0`, vertical separator, station title ("Station #01").
   - Right side: Wi-Fi status pill, stable status dot, and Maintainer wrench icon (`#btn-open-maintainer-sheet`).
2. **Customer Hero View (`#client-hero-view`):**
   - 60% Left: Big digital weight readout (`#live-weight-display`), stability pill (`#weight-stability-pill`), zero scale button.
   - 40% Right: Camera stream (`#vehicle-camera-feed`), license plate card (`#verified-plate-badge`), manual plate override button.
   - Bottom status strip: Action bar (`#action-bar-minimal`) with contextual status and "Print Slip" button.
3. **Maintainer Slide-Over Sheet (`#maintainer-sheet`):**
   - Contains tabbed diagnostics: Scale UART, Cameras & Crop, Cloud Sync, Wi-Fi Vault, Telemetry Logs, System Config.
   - Triggered by `#btn-open-maintainer-sheet` or `toggleMaintainerSheet()`.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/tests/test_web_server.py
git commit -m "feat(ui): restructure live index.html to 2-section customer hero and maintainer sheet"
```

---

### Task 3: Mirror Minimalist Architecture in Next.js + shadcn Frontend (`src/web/frontend/`)

**Dedicated Skill:** `@nextjs-app-router-patterns` / `@shadcn`

**Files:**
- Create: `hermes/src/web/frontend/components/kiosk/maintainer-sheet.tsx`
- Modify: `hermes/src/web/frontend/components/kiosk/operator-hud.tsx`
- Modify: `hermes/src/web/frontend/app/page.tsx`
- Test: `hermes/tests/test_shadcn_components.py`

**Step 1: Write the failing test**

Add assertions in `hermes/tests/test_shadcn_components.py`:
```python
    def test_maintainer_sheet_and_minimalist_page(self):
        root = Path(__file__).parent.parent
        kiosk_dir = root / "src" / "web" / "frontend" / "components" / "kiosk"
        page_file = root / "src" / "web" / "frontend" / "app" / "page.tsx"
        
        self.assertTrue((kiosk_dir / "maintainer-sheet.tsx").exists())
        page_content = page_file.read_text()
        self.assertIn("MaintainerSheet", page_content)
        self.assertIn("OperatorHUD", page_content)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_components.py -v`
Expected: FAIL

**Step 3: Implement minimal code in Next.js frontend**

1. Create `hermes/src/web/frontend/components/kiosk/maintainer-sheet.tsx`:
   - Accessible slide-over drawer housing developer tabs.
2. Refactor `hermes/src/web/frontend/components/kiosk/operator-hud.tsx`:
   - Ensure clean 60/40 customer view with large digital display, vehicle frame, and action bar.
3. Update `hermes/src/web/frontend/app/page.tsx`:
   - Mount `OperatorHUD` as primary single-view canvas.
   - Attach Maintainer trigger button in the app bar that opens `MaintainerSheet`.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_components.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/frontend/ hermes/tests/test_shadcn_components.py
git commit -m "feat(frontend): implement maintainer sheet and align next.js app with janus minimalist format"
```

---

### Task 4: Update Documentation in `docs/shadcn/` and Create Maintainer Guide

**Dedicated Skill:** `@writing-skills`

**Files:**
- Create: `hermes/docs/shadcn/sheet.md`
- Modify: `hermes/docs/shadcn/README.md`
- Test: `hermes/tests/test_shadcn_docs.py`

**Step 1: Write the failing test**

Update `hermes/tests/test_shadcn_docs.py` to require `sheet.md`:
```python
        required_components = ["card", "badge", "button", "tabs", "slider", "dialog", "sheet"]
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_docs.py -v`
Expected: FAIL

**Step 3: Implement minimal code**

1. Create `hermes/docs/shadcn/sheet.md` detailing the slide-over drawer props, keyboard accessibility, and maintainer usage.
2. Update `hermes/docs/shadcn/README.md` with link to `sheet.md`.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_docs.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/docs/shadcn/sheet.md hermes/docs/shadcn/README.md hermes/tests/test_shadcn_docs.py
git commit -m "docs(shadcn): add documentation for maintainer sheet component"
```

---

### Task 5: Holistic Verification Loop & Pre-Push Quality Gate

**Dedicated Skill:** `@verification-loop`

**Files:**
- Test: Full suites across Hermes (175+ tests), Argus (188 tests), and Janus (569 tests)
- Linter: `ruff check --fix` and `ty check`

**Step 1: Run Hermes verification suite**

Run: `cd /Users/kaalu/importante/hermes && uv run ruff check && uv run ty check && uv run pytest`
Expected: All checks pass, 0 errors, 0 warnings.

**Step 2: Run Argus verification suite**

Run: `cd /Users/kaalu/importante/argus && uv run ruff check && uv run ty check && PYTHONPATH=. uv run pytest -q`
Expected: 188 passed.

**Step 3: Run Janus verification suite**

Run: `cd /Users/kaalu/importante/janus && pnpm test`
Expected: 569 passed.

**Step 4: Live HTTP verification**

Run: `curl -I http://127.0.0.1:8080/`
Expected: HTTP 200 with clean header response.

---
