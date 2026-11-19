# Industrial Telemetry & Weighbridge Kiosk Dashboard Redesign Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the Hermes edge dashboard from amateur/AI-slop styling into an industrial-grade telemetry console (inspired by Mettler Toledo and Tesla Telemetry), featuring an Industrial Slate & Electric Mint palette, tabular monospace numeric stability, a distraction-free 60/40 single-dashboard customer view, and an accessible slide-over maintainer sheet.

**Architecture:**
- **Visual Design System:** Replaces generic saturated colors and glowing gradient borders with a grounded Industrial Slate (`#0C1014`), elevated matte surfaces (`#141A20`), hairline structural borders (`#222B35`), and functional semantic accents (Electric Mint `#10B981` for verified stability, Ochre Amber `#F59E0B` for debounce/motion, Hazard Red `#EF4444` for alarms).
- **Customer/Client View:** An asymmetrical 60/40 hero canvas. The left pane houses a massive digital scale display with `font-variant-numeric: tabular-nums` to eliminate jittering during live UART packet arrival. The right pane provides a clean 16:10 vehicle framing camera stream with an integrated license plate tag. The bottom strip houses tactile, high-contrast touch actions (min 48px hit targets for industrial touchscreens).
- **Maintainer Slide-Over Sheet:** A non-intrusive drawer housing hardware diagnostics (Scale UART `/dev/ttyAMA0 @ 1200 baud`, optical crop sliders, Wi-Fi failover, and telemetry ring buffer) accessible via a subtle header wrench icon or PIN without obscuring the client dashboard.
- **Lockstep Dual-Engine Parity:** Implemented on the live Flask edge interface (`src/web/templates/index.html` + `static/style.css`) and mirrored into the Next.js 16 + shadcn frontend (`src/web/frontend/`).

**Tech Stack:**
- CSS3 Custom Properties (OKLCH & Hex tokens) / Tailwind CSS (v4) / Tabular Typography
- Next.js 16 / React 19 / shadcn/ui (Radix primitives) / Lucide Icons
- Python 3.14 / Flask REST API / PySerial / SQLite WAL / Pytest

---

## Detailed Implementation Tasks

### Task 1: Establish Industrial Slate & Electric Mint Design System Tokens in `style.css`

**Dedicated Skill:** `@tailwind-design-system`

**Files:**
- Modify: `hermes/src/web/static/style.css`
- Test: `hermes/tests/test_industrial_design_tokens.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_industrial_design_tokens.py`:
```python
import unittest
from pathlib import Path

class TestIndustrialDesignTokens(unittest.TestCase):
    def test_industrial_palette_and_tabular_typography(self):
        root = Path(__file__).parent.parent
        css_file = root / "src" / "web" / "static" / "style.css"
        self.assertTrue(css_file.exists(), "Missing static/style.css")
        
        content = css_file.read_text()
        
        # Verify industrial dark slate base and elevated card surfaces
        self.assertIn("#0c1014", content.lower(), "Missing industrial slate base (#0c1014)")
        self.assertIn("#141a20", content.lower(), "Missing elevated matte card surface (#141a20)")
        self.assertIn("#222b35", content.lower(), "Missing hairline border (#222b35)")
        
        # Verify functional semantic accents (Electric Mint & Ochre Amber)
        self.assertIn("#10b981", content.lower(), "Missing electric mint (#10b981)")
        self.assertIn("#f59e0b", content.lower(), "Missing ochre amber (#f59e0b)")
        
        # Verify tabular nums rule to prevent number jittering on live scale updates
        self.assertIn("tabular-nums", content, "Missing tabular-nums rule for serial numbers")
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_industrial_design_tokens.py -v`
Expected: FAIL on missing hex tokens or tabular-nums rule.

**Step 3: Implement minimal CSS in `style.css`**

Update `hermes/src/web/static/style.css`:
- Define the root industrial token set:
  ```css
  :root {
    --bg-industrial-base: #0c1014;
    --bg-industrial-card: #141a20;
    --border-hairline: #222b35;
    --accent-electric-mint: #10b981;
    --accent-ochre-amber: #f59e0b;
    --accent-hazard-red: #ef4444;
    --text-high-contrast: #f0f4f8;
    --text-muted-steel: #8b949e;
  }
  ```
- Remove all cheesy decorative gradient overlays and replace with flat, clean, matte elevation.
- Add `.tabular-nums { font-variant-numeric: tabular-nums; }` and bind to `.hero-weight-display`, `#ov-weight`, and license plate outputs.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_industrial_design_tokens.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/static/style.css hermes/tests/test_industrial_design_tokens.py
git commit -m "style(ui): implement industrial slate design tokens and tabular numbers"
```

---

### Task 2: Re-architect 56px Industrial Header & System Metadata Bar

**Dedicated Skill:** `@clean-code`

**Files:**
- Modify: `hermes/src/web/templates/index.html`
- Test: `hermes/tests/test_industrial_header.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_industrial_header.py`:
```python
import unittest
from pathlib import Path

class TestIndustrialHeader(unittest.TestCase):
    def test_minimalist_header_structure(self):
        root = Path(__file__).parent.parent
        html = (root / "src" / "web" / "templates" / "index.html").read_text()
        
        # Verify 56px minimalist header container
        self.assertIn('id="industrial-header"', html)
        self.assertIn('id="station-meta-badge"', html)
        
        # Verify clean subtle status indicator (no giant badge soup)
        self.assertIn('id="hw-status-dot"', html)
        self.assertIn('id="btn-open-maintainer-sheet"', html)
        
        # Verify elimination of amateur badges from header
        self.assertNotIn('Zero Disk Wear &bull; In-RAM Processing', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_industrial_header.py -v`
Expected: FAIL

**Step 3: Implement minimal header code in `index.html`**

Update `header` in `hermes/src/web/templates/index.html`:
- Wrap header with `id="industrial-header"` (`h-14 border-b border-[#222b35] bg-[#0c1014]/90 backdrop-blur px-5 flex items-center justify-between`).
- Left brand lockup: Crisp SVG logo + "LUVOK HERMES" + Station Metadata badge (`id="station-meta-badge"` displaying `STATION #01 • WEIGHBRIDGE EDGE`).
- Center: Discrete mode indicator.
- Right: Single compact hardware status dot (`id="hw-status-dot"`, green dot with "System Online") and Maintainer Wrench Button (`#btn-open-maintainer-sheet`).
- Clean up redundant footer text ("Zero Disk Wear • In-RAM Processing") into a subtle technical watermark.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_industrial_header.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/tests/test_industrial_header.py
git commit -m "feat(ui): implement clean 56px industrial header without badge clutter"
```

---

### Task 3: Build 60/40 Customer Hero Canvas with Jitter-Free Digital Readout

**Dedicated Skill:** `@frontend-patterns`

**Files:**
- Modify: `hermes/src/web/templates/index.html`
- Modify: `hermes/src/web/static/style.css`
- Test: `hermes/tests/test_customer_hero_canvas.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_customer_hero_canvas.py`:
```python
import unittest
from pathlib import Path

class TestCustomerHeroCanvas(unittest.TestCase):
    def test_customer_hero_hierarchy(self):
        root = Path(__file__).parent.parent
        html = (root / "src" / "web" / "templates" / "index.html").read_text()
        
        # Verify 60/40 grid split
        self.assertIn('id="client-hero-view"', html)
        self.assertIn('id="hero-scale-pane"', html)
        self.assertIn('id="hero-camera-pane"', html)
        
        # Verify digital weight readout has tabular numbers and clean labels
        self.assertIn('id="live-weight-display"', html)
        self.assertIn('tabular-nums', html)
        self.assertIn('id="weight-stability-pill"', html)
        
        # Verify optical vehicle crop stage
        self.assertIn('id="vehicle-camera-feed"', html)
        self.assertIn('id="verified-plate-badge"', html)
        
        # Ensure amateur label "STATE: IDLE" is removed in favor of clean status pill
        self.assertNotIn('STATE: IDLE', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_customer_hero_canvas.py -v`
Expected: FAIL

**Step 3: Implement minimal code in `index.html` and `style.css`**

1. In `src/web/templates/index.html`:
   - Left 60% (`#hero-scale-pane`):
     - Matte card surface (`bg-[#141a20] border border-[#222b35] rounded-xl p-8`).
     - Header: Scale icon, "GROSS WEIGHT", and dynamic stability pill (`#weight-stability-pill`, `STABLE` in Electric Mint `#10b981` / `SAMPLING` in Ochre Amber `#f59e0b`).
     - Readout: Massive, razor-sharp digital weight numbers (`#ov-weight`, `text-7xl lg:text-8xl font-mono font-bold tabular-nums tracking-tight text-white`).
     - Sub-bar: Clean session reference and last confirmed weight.
   - Right 40% (`#hero-camera-pane`):
     - 16:10 aspect vehicle camera frame (`#vehicle-camera-feed`) with 1px border.
     - License Plate Card (`#verified-plate-badge`): Bold off-white registration number with confidence rating (`#ov-anpr-confidence`).
2. Update `style.css` to ensure tight spacing, zero gradient bleeds, and smooth number transition.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_customer_hero_canvas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_customer_hero_canvas.py
git commit -m "feat(ui): implement 60/40 customer hero canvas with jitter-free tabular readout"
```

---

### Task 4: Implement Tactile Industrial Touch Action Bar & Override Dialog

**Dedicated Skill:** `@shadcn`

**Files:**
- Modify: `hermes/src/web/templates/index.html`
- Modify: `hermes/src/web/static/style.css`
- Test: `hermes/tests/test_tactile_action_bar.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_tactile_action_bar.py`:
```python
import unittest
from pathlib import Path

class TestTactileActionBar(unittest.TestCase):
    def test_tactile_buttons_and_dialog(self):
        root = Path(__file__).parent.parent
        html = (root / "src" / "web" / "templates" / "index.html").read_text()
        
        # Verify minimal touch action bar
        self.assertIn('id="action-bar-minimal"', html)
        self.assertIn('id="btn-zero-scale"', html)
        self.assertIn('id="btn-print-slip"', html)
        self.assertIn('id="btn-override-plate"', html)
        
        # Verify tactile button styling classes
        self.assertIn('industrial-btn', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_tactile_action_bar.py -v`
Expected: FAIL

**Step 3: Implement minimal code in `index.html` and `style.css`**

1. In `src/web/static/style.css`:
   - Define `.industrial-btn`:
     - Height: Minimum 48px (`min-h-12`) with tactile micro-depression on active (`active:translate-y-0.5`).
     - Neutral matte dark button styling with high-contrast text and subtle border.
2. In `src/web/templates/index.html`:
   - `#action-bar-minimal`:
     - "Zero Scale" (`#btn-zero-scale`): Clears tare/zero when platform is idle.
     - "Print Slip" (`#btn-print-slip`): High-visibility electric mint primary button enabled on stable weight.
     - "Override Plate" (`#btn-override-plate`): Opens keyboard dialog if OCR needs operator verification.
     - Maintain existing micro-action aliases (`btn-quick-edit-plate`, `btn-quick-print-slip`, `contextual-action-bar`) so existing tests continue passing 100%.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_tactile_action_bar.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_tactile_action_bar.py
git commit -m "feat(ui): implement tactile industrial touch action bar with min 48px targets"
```

---

### Task 5: Restructure Slide-Over Maintainer Diagnostic Sheet

**Dedicated Skill:** `@ui-ux-pro-max`

**Files:**
- Modify: `hermes/src/web/templates/index.html`
- Modify: `hermes/src/web/static/style.css`
- Test: `hermes/tests/test_maintainer_sheet_diagnostics.py`

**Step 1: Write the failing test**

Create `hermes/tests/test_maintainer_sheet_diagnostics.py`:
```python
import unittest
from pathlib import Path

class TestMaintainerSheetDiagnostics(unittest.TestCase):
    def test_maintainer_sheet_structure(self):
        root = Path(__file__).parent.parent
        html = (root / "src" / "web" / "templates" / "index.html").read_text()
        
        # Verify maintainer sheet container and tabs
        self.assertIn('id="maintainer-sheet"', html)
        self.assertIn('id="maintainer-sheet-overlay"', html)
        self.assertIn('id="maintainer-tab-scale"', html)
        self.assertIn('id="maintainer-tab-crop"', html)
        self.assertIn('id="maintainer-tab-network"', html)
        self.assertIn('id="maintainer-tab-telemetry"', html)
        
        # Verify all 8 crop sliders and inputs remain accessible in the sheet
        for slider in ["crop_pad_top_slider", "crop_pad_bottom_slider", "crop_pad_left_slider", "crop_pad_right_slider"]:
            self.assertIn(f'id="{slider}"', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_maintainer_sheet_diagnostics.py -v`
Expected: FAIL

**Step 3: Implement minimal code in `index.html` and `style.css`**

1. Format `#maintainer-sheet` into a clean right slide-over drawer (`width: 440px`, elevated dark slate `#141a20`, border-l `#222b35`):
   - Header: Wrench icon, "Edge System Diagnostics", close X button.
   - Segmented Tab Bar: Scale UART, Optical Crop, Network & Hotspot, Telemetry Logs.
   - Clean grouping cards for serial baud rates, crop sliders, and Wi-Fi failover settings.
2. Maintain existing IDs (`admin-drawer`, `admin-drawer-overlay`, `admin-drawer-login-form`, `admin-drawer-content`, all 8 sliders) so all previous test suites remain green.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_maintainer_sheet_diagnostics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_maintainer_sheet_diagnostics.py
git commit -m "feat(ui): format maintainer slide-over diagnostics sheet with structured tabs"
```

---

### Task 6: Synchronize Next.js 16 + shadcn Frontend (`src/web/frontend/`)

**Dedicated Skill:** `@nextjs-app-router-patterns`

**Files:**
- Modify: `hermes/src/web/frontend/app/globals.css`
- Modify: `hermes/src/web/frontend/components/kiosk/operator-hud.tsx`
- Modify: `hermes/src/web/frontend/components/kiosk/maintainer-sheet.tsx`
- Modify: `hermes/src/web/frontend/app/page.tsx`
- Test: `hermes/tests/test_shadcn_components.py`

**Step 1: Write the failing test**

Add assertions in `hermes/tests/test_shadcn_components.py`:
```python
    def test_industrial_nextjs_tokens_and_hud(self):
        root = Path(__file__).parent.parent
        css_file = root / "src" / "web" / "frontend" / "app" / "globals.css"
        hud_file = root / "src" / "web" / "frontend" / "components" / "kiosk" / "operator-hud.tsx"
        
        css_content = css_file.read_text()
        self.assertIn("tabular-nums", css_content)
        
        hud_content = hud_file.read_text()
        self.assertIn("tabular-nums", hud_content)
        self.assertIn("STABLE", hud_content)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_components.py -k "test_industrial_nextjs_tokens_and_hud" -v`
Expected: FAIL

**Step 3: Implement minimal code in Next.js frontend**

1. Update `src/web/frontend/app/globals.css`:
   - Set `--background: #0c1014`, `--card: #141a20`, `--border: #222b35`, `--primary: #10b981`.
   - Add `.tabular-nums` class.
2. Update `src/web/frontend/components/kiosk/operator-hud.tsx`:
   - Apply `tabular-nums` and the 60/40 industrial layout.
3. Update `src/web/frontend/components/kiosk/maintainer-sheet.tsx`:
   - Ensure matching matte surfaces, clean tab typography, and min 48px tactile actions.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_shadcn_components.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/frontend/ hermes/tests/test_shadcn_components.py
git commit -m "feat(frontend): sync next.js app router frontend to industrial design system"
```

---

### Task 7: Holistic Multi-Repo Verification & Quality Gate

**Dedicated Skill:** `@verification-loop`

**Files:**
- Test: Full suites across Hermes (180+ tests), Argus (194 tests), and Janus (569 tests)
- Linter: `uv run ruff check` and `uv run ty check`

**Step 1: Run Hermes verification suite**

Run: `cd /Users/kaalu/importante/hermes && uv run ruff check && uv run ty check && uv run pytest`
Expected: All checks pass, 0 errors, 0 warnings.

**Step 2: Run Argus verification suite**

Run: `cd /Users/kaalu/importante/argus && uv run ruff check && uv run ty check && PYTHONPATH=. uv run pytest -q`
Expected: 194 passed.

**Step 3: Run Janus verification suite**

Run: `cd /Users/kaalu/importante/janus && pnpm test`
Expected: 569 passed.

**Step 4: Live HTTP Endpoint Verification**

Run: `/Users/kaalu/importante/hermes/.venv/bin/python -c "from src.web.app import create_app; c = create_app().test_client(); r = c.get('/'); assert r.status_code == 200; assert b'#0c1014' in r.data or b'industrial-header' in r.data; print('Live HTTP Verification OK')"`
Expected: `Live HTTP Verification OK`

---
