# Hermes Minimalist Operational HUD & Admin Drawer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Hermes edge console into a "Maximalist Functioning, Minimalist Design" interface featuring a clean Split Hero Operational HUD (Live Digital Scale + Auto-Cropped Vehicle Plate) and a locked Slide-Over Admin Drawer for technical configuration, completely eliminating routine button clutter for weighbridge operators.

**Architecture:** Replace the 7 persistent navigation tab buttons in `src/web/templates/index.html` with an unobtrusive 4-subsystem health strip (`Scale`, `ANPR`, `Sync`, `Network`) and a single gear settings trigger. The main screen becomes a 60/40 Split Hero Kiosk: Left 60% displays massive live scale weight and stability states; Right 40% displays live vehicle crop snapshots and verified plate badges. All technical controls (crop padding sliders, RTSP URLs, UART baudrate, Wi-Fi scanning, raw telemetry logs) are consolidated inside a slide-over drawer requiring superadmin authentication (`Gluvok@241821`), preserving all existing DOM IDs and API contracts.

**Tech Stack:** Python 3.14, Flask application factory, Offline-first CSS with Janus OKLCH dark palette, Lucide Icons, Vanilla JS state synchronization, Pytest.

**Relevant Skills Orchestration:**
- Task 1: `@clean-code` - Ruthless simplification of the top navigation bar, eliminating 7 tab buttons in favor of an unobtrusive health indicator strip.
- Task 2: `@ui-ux-pro-max` - High-contrast industrial Split Hero HUD layout, massive scale typography, vehicle framing card, and zero-button automated workflow.
- Task 3: `@design` - Sleek right slide-over superadmin drawer with backdrop blur, accordion hardware configuration panels, and smooth transition mechanics.
- Task 4: `@taste` - Contextual micro-actions (plate correction, print slip) fading in on completion without polluting the idle screen.
- Task 5: `@verification-loop` - Comprehensive cross-repo test suites (Hermes 160+, Argus 200, Janus 562), static analysis, and real HTML curl testing.

---

### Task 1: Subsystem Health Strip & Header Simplification

**Dedicated Skill:** `@clean-code` (pragmatic simplicity, eliminating UI verbosity, maintaining DOM contracts and minimal diff footprint)

**Files:**
- Modify: `hermes/src/web/templates/index.html:30-80`
- Modify: `hermes/src/web/static/style.css:480-560`
- Test: `hermes/tests/test_web_server.py:100-140`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_minimalist_header_and_health_strip`:

```python
    def test_minimalist_header_and_health_strip(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Header has compact health status strip
        self.assertIn('id="health-strip"', html)
        self.assertIn('id="health-scale-pill"', html)
        self.assertIn('id="health-anpr-pill"', html)
        self.assertIn('id="health-sync-pill"', html)
        self.assertIn('id="health-wifi-pill"', html)

        # Admin settings gear button is present
        self.assertIn('id="btn-open-admin-drawer"', html)

        # Verbose tab buttons are replaced with clean kiosk header
        self.assertNotIn('class="nav-tabs-container"', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_minimalist_header_and_health_strip -v`
Expected: FAIL with `AssertionError: 'id="health-strip"' not found in '...'`

**Step 3: Write minimal implementation**

In `hermes/src/web/templates/index.html`, replace the horizontal navigation tabs container (lines 40-75) with the compact 4-subsystem health strip and admin drawer trigger:

```html
    <!-- Compact Subsystem Health Strip & Admin Trigger -->
    <div class="top-nav-center">
      <div id="health-strip" class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-card border border-border text-xs">
        <span id="health-scale-pill" class="inline-flex items-center gap-1.5 font-medium text-muted-foreground">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Scale
        </span>
        <span class="text-border">&bull;</span>
        <span id="health-anpr-pill" class="inline-flex items-center gap-1.5 font-medium text-muted-foreground">
          <span class="w-2 h-2 rounded-full bg-zinc-500"></span> ANPR
        </span>
        <span class="text-border">&bull;</span>
        <span id="health-sync-pill" class="inline-flex items-center gap-1.5 font-medium text-muted-foreground">
          <span class="w-2 h-2 rounded-full bg-amber-400"></span> Sync
        </span>
        <span class="text-border">&bull;</span>
        <span id="health-wifi-pill" class="inline-flex items-center gap-1.5 font-medium text-muted-foreground">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span> Wi-Fi
        </span>
      </div>
    </div>

    <!-- Top Nav Right Actions -->
    <div class="top-nav-right">
      <button onclick="toggleAdminDrawer()" id="btn-open-admin-drawer" class="btn btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5">
        <i data-lucide="settings" class="w-3.5 h-3.5 text-muted-foreground"></i>
        <span>Settings</span>
      </button>
    </div>
```

In `hermes/src/web/static/style.css`, add styles for `.top-nav-center` and health pill states.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_minimalist_header_and_health_strip -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_web_server.py
git commit -m "feat(ui): implement minimalist header with 4-subsystem health strip"
```

---

### Task 2: Split Hero Operational Heads-Up Display (60/40 Kiosk)

**Dedicated Skill:** `@ui-ux-pro-max` (WCAG AA accessibility > 4.5:1 contrast, massive digital scale typography, automated zero-click workflow)

**Files:**
- Modify: `hermes/src/web/templates/index.html:85-350`
- Modify: `hermes/src/web/static/style.css:200-320`
- Test: `hermes/tests/test_web_server.py:140-180`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_split_hero_hud_layout_elements`:

```python
    def test_split_hero_hud_layout_elements(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Split Hero HUD containers present
        self.assertIn('id="hud-scale-column"', html)
        self.assertIn('id="hud-vehicle-column"', html)

        # Hero Scale Display elements preserved
        self.assertIn('id="ov-weight"', html)
        self.assertIn('id="scale-page-weight"', html)
        self.assertIn('id="scale-state-detail"', html)

        # Vehicle Framing & ANPR Crop elements preserved
        self.assertIn('id="ov-anpr-plate"', html)
        self.assertIn('id="ov-anpr-crop-stage"', html)
        self.assertIn('id="ov-anpr-confidence"', html)
        self.assertIn('id="ov-sync-status-badge"', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_split_hero_hud_layout_elements -v`
Expected: FAIL with `AssertionError: 'id="hud-scale-column"' not found in '...'`

**Step 3: Write minimal implementation**

Structure the main operational area in `hermes/src/web/templates/index.html` as a clean 2-column grid:

```html
<main class="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
    
    <!-- LEFT 60%: HERO LIVE SCALE INDICATOR -->
    <div id="hud-scale-column" class="lg:col-span-7 flex flex-col gap-4">
      <div class="p-8 rounded-2xl bg-card border border-border shadow-lg flex-1 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i data-lucide="scale" class="w-5 h-5 text-emerald-400"></i>
            <span class="text-sm font-bold uppercase tracking-wider text-muted-foreground font-mono">Live Weighbridge Scale</span>
          </div>
          <span id="scale-state-detail" class="px-3 py-1 rounded-full text-xs font-bold bg-secondary text-foreground font-mono">
            STATE: IDLE
          </span>
        </div>

        <!-- Massive Monospace Weight Display -->
        <div class="my-10 text-center space-y-2">
          <div id="ov-weight" class="text-7xl lg:text-8xl font-black font-mono tracking-tight text-emerald-400">
            0.000 <span class="text-3xl font-normal text-muted-foreground">kg</span>
          </div>
          <div id="scale-page-weight" class="hidden">0.000 kg</div>
          <p id="scale-stability-hint" class="text-xs text-muted-foreground font-mono">
            Automatic Trigger: &gt; <span id="scale-thresh-disp" class="text-emerald-400 font-bold">50.0 kg</span> continuous stability
          </p>
        </div>

        <!-- Recent Weighments Mini-Ticker -->
        <div class="pt-4 border-t border-border/60 flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Last Weighment: <strong id="last-weighed-weight" class="text-foreground">--</strong></span>
          <span>Plate: <strong id="last-weighed-plate" class="text-primary">--</strong></span>
          <span>Time: <span id="last-weighed-time">--</span></span>
        </div>
      </div>
    </div>

    <!-- RIGHT 40%: VEHICLE CROP & ANPR CARD -->
    <div id="hud-vehicle-column" class="lg:col-span-5 flex flex-col gap-4">
      <div class="p-6 rounded-2xl bg-card border border-border shadow-lg flex-1 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <i data-lucide="camera" class="w-5 h-5 text-primary"></i>
            <span class="text-sm font-bold uppercase tracking-wider text-muted-foreground font-mono">Vehicle Camera & Crop</span>
          </div>
          <span id="ov-sync-status-badge" class="badge badge-emerald">AUTOMATED</span>
        </div>

        <!-- Live Vehicle Framing Preview Stage -->
        <div id="ov-anpr-crop-stage" class="my-4 relative aspect-[16/10] rounded-xl bg-zinc-950 border border-border overflow-hidden flex items-center justify-center">
          <img id="ov-anpr-crop-img" src="" alt="Vehicle Framing" class="w-full h-full object-cover hidden" />
          <div id="ov-anpr-placeholder" class="text-center p-4 space-y-2">
            <i data-lucide="truck" class="w-10 h-10 text-muted-foreground mx-auto stroke-[1.5]"></i>
            <p class="text-xs text-muted-foreground font-mono">Awaiting Vehicle on Scale</p>
          </div>
        </div>

        <!-- Verified License Plate Badge -->
        <div class="p-4 rounded-xl bg-secondary border border-border flex items-center justify-between">
          <div>
            <div class="text-2xs uppercase tracking-widest text-muted-foreground font-mono font-medium">Recognized Plate</div>
            <div id="ov-anpr-plate" class="text-2xl font-black font-mono tracking-widest text-primary">READY</div>
            <div id="ov-session-plate" class="hidden">READY</div>
          </div>
          <div class="text-right">
            <div class="text-2xs uppercase tracking-widest text-muted-foreground font-mono">Confidence</div>
            <div id="ov-anpr-confidence" class="text-sm font-bold font-mono text-emerald-400">--%</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</main>
```

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_split_hero_hud_layout_elements -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_web_server.py
git commit -m "feat(ui): implement split hero operational HUD layout"
```

---

### Task 3: Slide-Over Superadmin Settings Drawer

**Dedicated Skill:** `@design` (clean slide-over overlay with backdrop blur, accordion hardware configuration panels, and smooth transition mechanics)

**Files:**
- Modify: `hermes/src/web/templates/index.html:350-700`
- Modify: `hermes/src/web/static/style.css:560-708`
- Test: `hermes/tests/test_web_server.py:180-220`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_slide_over_admin_drawer_and_preserved_controls`:

```python
    def test_slide_over_admin_drawer_and_preserved_controls(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Slide-over admin drawer structure is present
        self.assertIn('id="admin-drawer"', html)
        self.assertIn('id="admin-drawer-overlay"', html)
        self.assertIn('id="admin-drawer-login-form"', html)
        self.assertIn('id="admin-drawer-content"', html)

        # All 8 vehicle crop configuration sliders & inputs preserved
        self.assertIn('id="crop_pad_top_slider"', html)
        self.assertIn('id="crop_pad_bottom_slider"', html)
        self.assertIn('id="crop_pad_left_slider"', html)
        self.assertIn('id="crop_pad_right_slider"', html)
        self.assertIn('id="cfg-crop-pad-top"', html)
        self.assertIn('id="cfg-crop-pad-bottom"', html)
        self.assertIn('id="cfg-crop-pad-left"', html)
        self.assertIn('id="cfg-crop-pad-right"', html)

        # Camera URLs, serial UART, Wi-Fi inputs preserved
        self.assertIn('id="cfg-anpr-url"', html)
        self.assertIn('id="cfg-serial-port"', html)
        self.assertIn('id="cfg-serial-baud"', html)
        self.assertIn('id="telemetry-log-stream"', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_slide_over_admin_drawer_and_preserved_controls -v`
Expected: FAIL with `AssertionError: 'id="admin-drawer"' not found in '...'`

**Step 3: Write minimal implementation**

In `hermes/src/web/templates/index.html`, implement the `#admin-drawer` container placed just before `</body>`:
- Backdrop overlay: `id="admin-drawer-overlay"` (clicking closes drawer).
- Drawer panel: `id="admin-drawer"` (`fixed top-0 right-0 bottom-0 w-full max-w-xl bg-card border-l border-border shadow-2xl z-50 transform translate-x-full transition-transform duration-300`).
- Gate 1: If unauthenticated, displays PIN/Password login prompt with `#admin-drawer-login-form`.
- Gate 2: If authenticated (`hasAdminSession()`), displays categorized accordion panels:
  1. `Camera & Vehicle Framing Tuning`: Live crop sliders (`#crop_pad_top_slider`, etc.) + RTSP URLs.
  2. `Weighbridge Scale UART`: Port, baudrate, threshold.
  3. `Local Network & Wi-Fi`: Saved networks, scan, hotspot toggle.
  4. `Telemetry & Maintenance`: Live streaming logs console (`#telemetry-log-stream`) + Restart service button.

In `src/web/static/style.css`, add the drawer transitions:
```css
.drawer-open {
  transform: translateX(0) !important;
}
.drawer-backdrop-open {
  opacity: 1 !important;
  pointer-events: auto !important;
}
```

In `index.html` `<script>`, add `toggleAdminDrawer()`, `openAdminDrawer()`, and `closeAdminDrawer()`.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_slide_over_admin_drawer_and_preserved_controls -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_web_server.py
git commit -m "feat(ui): implement slide-over admin settings drawer for technical tuning"
```

---

### Task 4: Contextual Edge-Case Micro-Actions & Auto-Archiving

**Dedicated Skill:** `@taste` (contextual micro-actions that only fade in upon weighment completion, leaving the idle screen 100% buttonless)

**Files:**
- Modify: `hermes/src/web/templates/index.html:700-850`
- Modify: `hermes/src/web/static/style.css:320-370`
- Test: `hermes/tests/test_web_server.py:220-250`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_contextual_micro_actions_present`:

```python
    def test_contextual_micro_actions_present(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Contextual micro-action bar exists and is initially hidden
        self.assertIn('id="contextual-action-bar"', html)
        self.assertIn('id="btn-quick-edit-plate"', html)
        self.assertIn('id="btn-quick-print-slip"', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_contextual_micro_actions_present -v`
Expected: FAIL with `AssertionError: 'id="contextual-action-bar"' not found in '...'`

**Step 3: Write minimal implementation**

In `hermes/src/web/templates/index.html`:
- Add `#contextual-action-bar` beneath the verified plate badge.
- When an ANPR plate is confirmed, `#contextual-action-bar` smoothly fades in with:
  - `Edit Plate` (opens a small modal input to correct an obscured digit if needed)
  - `Print Slip` (triggers ticket printing)
- Automatically hides after 15 seconds or when the scale drops back to zero/IDLE.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::TestFlaskDiagnosticsApp::test_contextual_micro_actions_present -v`
Expected: PASS

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/src/web/static/style.css hermes/tests/test_web_server.py
git commit -m "feat(ui): add contextual micro-action triggers for post-weighment operations"
```

---

### Task 5: Multi-Repo Verification & Field Gate Check

**Dedicated Skill:** `@verification-loop` (holistic multi-phase verification across Hermes, Argus, Janus, static analysis, and real HTML curl testing)

**Files:**
- Test: All suites across Hermes, Argus, and Janus

**Step 1: Run complete Hermes test suite**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/ -v`
Expected: All 160+ tests PASS without error.

**Step 2: Run Argus test suite**

Run: `cd /Users/kaalu/importante/argus && PYTHONPATH=. .venv/bin/pytest tests/ -q`
Expected: 200 passed.

**Step 3: Run Janus test suite**

Run: `cd /Users/kaalu/importante/janus && npm test`
Expected: 562 passed.

**Step 4: Run static analysis and linting**

Run: `cd /Users/kaalu/importante/hermes && ruff check .`
Expected: All checks pass, 0 violations.

**Step 5: Verify live rendered HTML with curl**

Start temporary test server or run Flask client test:
Run: `/Users/kaalu/importante/hermes/.venv/bin/python -c "from src.web.app import create_app; c = create_app().test_client(); r = c.get('/'); assert r.status_code == 200; print('Rendered HTML check PASSED')"`
Expected: `Rendered HTML check PASSED`

**Step 6: Commit and Push**

```bash
git status
git push origin feat/durability-offline-queue-and-secrets-hardening
```
