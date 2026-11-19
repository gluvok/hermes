# Hermes Light Mode & Concise Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Hermes edge web console to Janus light mode using native OKLCH tokens and streamline navigation bar tab labels to concise, readable titles.

**Architecture:** Replace dark `:root` definitions in `src/web/static/style.css` with Janus's light palette tokens (`--background: oklch(0.986 0.005 130)`, `--foreground: oklch(0.18 0.015 150)`, `--card: oklch(1 0 0)`, `--primary: oklch(0.42 0.065 155)`, etc.) while preserving `--bg-base: #09090b` fallback compatibility. Update `src/web/templates/index.html` to remove `.dark`, shorten navigation labels ("Scale", "Cameras", "Sync", "Logs", "Config", "Wi-Fi"), and tune all surfaces and badges for WCAG AA compliance (> 4.5:1 contrast).

**Tech Stack:** Python 3.14, Flask, Static CSS with OKLCH color variables (zero external CDN dependencies), Lucide Icons, Pytest.

**Relevant Skills:**
- `@writing-plans`: Implementation task structure, TDD cycles, exact paths and commands.
- `@clean-code`: Clean, minimal, pragmatic changes without over-engineering.
- `@test-driven-development`: Red-Green-Refactor testing on Flask routes and static assets.
- `@verification-loop`: Multi-repo cross-verification across Hermes, Argus, and Janus.

---

### Task 1: Janus OKLCH Light Mode Token Architecture

**Files:**
- Modify: `hermes/src/web/static/style.css:1-68`
- Test: `hermes/tests/test_web_server.py:75-100`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_static_stylesheet_light_mode_tokens`:

```python
    def test_static_stylesheet_light_mode_tokens(self):
        css_res = self.client.get("/static/style.css")
        self.assertEqual(css_res.status_code, 200)
        css_text = css_res.get_data(as_text=True)
        # Verify light mode tokens in :root
        self.assertIn("--background: oklch(0.986 0.005 130)", css_text)
        self.assertIn("--foreground: oklch(0.18 0.015 150)", css_text)
        self.assertIn("--card: oklch(1 0 0)", css_text)
        self.assertIn("--primary: oklch(0.42 0.065 155)", css_text)
        self.assertIn("--secondary: oklch(0.96 0.008 140)", css_text)
        self.assertIn("--muted: oklch(0.96 0.008 140)", css_text)
        self.assertIn("--border: oklch(0.915 0.008 135)", css_text)
        # Verify backward compatibility fallback alias
        self.assertIn("--bg-base: #09090b", css_text)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::WebServerTests::test_static_stylesheet_light_mode_tokens -v`
Expected: FAIL with `AssertionError: '--background: oklch(0.986 0.005 130)' not found in '...'`

**Step 3: Write minimal implementation**

Update `hermes/src/web/static/style.css` `:root` tokens (lines 8-68) to match Janus's exact light theme:

```css
:root {
  /* Exact Janus Light Mode OKLCH Design Tokens */
  --background: oklch(0.986 0.005 130);
  --foreground: oklch(0.18 0.015 150);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.18 0.015 150);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.18 0.015 150);
  --primary: oklch(0.42 0.065 155);
  --primary-foreground: oklch(0.99 0 0);
  --secondary: oklch(0.96 0.008 140);
  --secondary-foreground: oklch(0.22 0.015 150);
  --muted: oklch(0.96 0.008 140);
  --muted-foreground: oklch(0.54 0.018 150);
  --accent: oklch(0.95 0.012 155);
  --accent-foreground: oklch(0.2 0.025 155);
  --destructive: oklch(0.58 0.16 28);
  --border: oklch(0.915 0.008 135);
  --input: oklch(0.915 0.008 135);
  --ring: oklch(0.55 0.06 155);

  /* Janus Chart & Accent Palette */
  --chart-1: oklch(0.42 0.065 155);
  --chart-2: oklch(0.58 0.08 140);
  --chart-3: oklch(0.68 0.08 75);
  --chart-4: oklch(0.58 0.12 28);
  --chart-5: oklch(0.54 0.018 150);

  /* Janus Sidebar Tokens */
  --sidebar: oklch(0.986 0.005 130);
  --sidebar-foreground: oklch(0.18 0.015 150);
  --sidebar-primary: oklch(0.42 0.065 155);
  --sidebar-primary-foreground: oklch(0.99 0 0);
  --sidebar-accent: oklch(0.95 0.012 155);
  --sidebar-accent-foreground: oklch(0.2 0.025 155);
  --sidebar-border: oklch(0.915 0.008 135);
  --sidebar-ring: oklch(0.55 0.06 155);

  /* Janus Mapped Component Tokens */
  --canvas-deep: oklch(0.96 0.008 140);
  --accent-emerald: oklch(0.42 0.065 155);
  --accent-sky: oklch(0.50 0.12 230);
  --accent-amber: oklch(0.55 0.12 75);
  --accent-rose: oklch(0.58 0.16 28);
  --accent-violet: oklch(0.52 0.14 285);
  --radius: 0.625rem;

  /* Backward Compatibility & Fallback Aliases */
  --bg-base: #09090b;
  --bg-card: var(--card);
  --bg-card-hover: oklch(0.95 0.012 155);
  --bg-muted: var(--muted);
  --bg-accent: var(--accent);
  --border-hex: #e4e4e7;
  --border-light: oklch(0.915 0.008 135);

  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
```

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::WebServerTests::test_static_stylesheet_light_mode_tokens -v`
Expected: PASS (1 passed)

**Step 5: Commit**

```bash
git add hermes/src/web/static/style.css hermes/tests/test_web_server.py
git commit -m "feat(web): map root tokens to Janus OKLCH light mode palette"
```

---

### Task 2: Concise Navigation Bar & Clean Document Root

**Files:**
- Modify: `hermes/src/web/templates/index.html:1-75`
- Test: `hermes/tests/test_web_server.py:100-135`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_concise_navigation_labels_and_light_theme_root`:

```python
    def test_concise_navigation_labels_and_light_theme_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        # Root document has light theme or default clean root without forced dark class
        self.assertNotIn('<html lang="en" class="dark">', html)
        self.assertIn('<html lang="en"', html)

        # Navigation labels are concise
        self.assertIn('id="nav-item-overview"', html)
        self.assertIn('<span>Overview</span>', html)
        self.assertIn('id="nav-item-scale"', html)
        self.assertIn('<span>Scale</span>', html)
        self.assertIn('id="nav-item-anpr"', html)
        self.assertIn('<span>Cameras</span>', html)
        self.assertIn('id="nav-item-cloud"', html)
        self.assertIn('<span>Sync</span>', html)
        self.assertIn('id="nav-item-telemetry"', html)
        self.assertIn('<span>Logs</span>', html)
        self.assertIn('id="nav-item-config"', html)
        self.assertIn('<span>Config</span>', html)
        self.assertIn('id="nav-item-wifi"', html)
        self.assertIn('<span>Wi-Fi</span>', html)

        # Verbose labels removed
        self.assertNotIn('<span>Scale Indicator</span>', html)
        self.assertNotIn('<span>Cameras & Crop</span>', html)
        self.assertNotIn('<span>Cloud Transfer</span>', html)
        self.assertNotIn('<span>Telemetry Logs</span>', html)
        self.assertNotIn('<span>System Config</span>', html)
        self.assertNotIn('<span>Wi-Fi Setup</span>', html)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::WebServerTests::test_concise_navigation_labels_and_light_theme_root -v`
Expected: FAIL with `AssertionError: '<html lang="en" class="dark">' unexpectedly found in '...'`

**Step 3: Write minimal implementation**

In `hermes/src/web/templates/index.html`:
1. Change `<html lang="en" class="dark">` to `<html lang="en">`.
2. Update the navigation buttons (lines 43-73) with concise labels:

```html
      <!-- Horizontal Navigation Tabs -->
      <nav class="nav-tabs-container">
        <button onclick="switchTab('overview')" id="nav-item-overview" class="nav-tab-btn active">
          <i data-lucide="layout-dashboard" class="w-4 h-4 text-emerald-600"></i>
          <span>Overview</span>
        </button>
        <button onclick="switchTab('scale')" id="nav-item-scale" class="nav-tab-btn">
          <i data-lucide="scale" class="w-4 h-4"></i>
          <span>Scale</span>
        </button>
        <button onclick="switchTab('anpr')" id="nav-item-anpr" class="nav-tab-btn">
          <i data-lucide="camera" class="w-4 h-4"></i>
          <span>Cameras</span>
        </button>
        <button onclick="switchTab('cloud')" id="nav-item-cloud" class="nav-tab-btn">
          <i data-lucide="cloud-upload" class="w-4 h-4"></i>
          <span>Sync</span>
        </button>
        <button onclick="switchTab('telemetry')" id="nav-item-telemetry" class="nav-tab-btn">
          <i data-lucide="terminal" class="w-4 h-4"></i>
          <span>Logs</span>
        </button>
        <button onclick="switchTab('config')" id="nav-item-config" class="nav-tab-btn">
          <i data-lucide="sliders-horizontal" class="w-4 h-4 text-amber-600"></i>
          <span>Config</span>
        </button>
        <button onclick="switchTab('wifi')" id="nav-item-wifi" class="nav-tab-btn">
          <i data-lucide="wifi" class="w-4 h-4 text-sky-600"></i>
          <span>Wi-Fi</span>
        </button>
      </nav>
```

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::WebServerTests::test_concise_navigation_labels_and_light_theme_root -v`
Expected: PASS (1 passed)

**Step 5: Commit**

```bash
git add hermes/src/web/templates/index.html hermes/tests/test_web_server.py
git commit -m "feat(web): update root to light mode and shorten nav tab labels"
```

---

### Task 3: Component Surfaces, Forms, Badges & High-Contrast Light Mode Styling

**Files:**
- Modify: `hermes/src/web/static/style.css:320-707`
- Test: `hermes/tests/test_web_server.py:135-170`

**Step 1: Write the failing test**

Edit `hermes/tests/test_web_server.py` to add `test_light_mode_component_contrast_and_surfaces`:

```python
    def test_light_mode_component_contrast_and_surfaces(self):
        css_res = self.client.get("/static/style.css")
        self.assertEqual(css_res.status_code, 200)
        css = css_res.get_data(as_text=True)

        # Form elements have light mode background and input border
        self.assertIn("input[type=\"text\"]", css)
        self.assertIn("background: var(--card)", css)
        self.assertIn("border: 1px solid var(--input)", css)

        # Top nav uses light translucent card background
        self.assertIn(".top-nav {", css)
        self.assertIn("background-color: oklch(1 0 0 / 92%)", css)

        # Active nav button elevated light pill styling
        self.assertIn(".nav-tab-btn.active", css)
        self.assertIn("background: var(--card)", css)
        self.assertIn("color: var(--foreground)", css)

        # High-contrast light badges
        self.assertIn(".badge-emerald", css)
        self.assertIn("color: oklch(0.32 0.08 155)", css)
```

**Step 2: Run test to verify it fails**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::WebServerTests::test_light_mode_component_contrast_and_surfaces -v`
Expected: FAIL with `AssertionError: 'background: var(--card)' not found in '...'`

**Step 3: Write minimal implementation**

Update `hermes/src/web/static/style.css`:
1. **Top Nav Bar:**
   ```css
   .top-nav {
     position: sticky;
     top: 0;
     z-index: 50;
     background-color: oklch(1 0 0 / 92%);
     backdrop-filter: blur(12px);
     -webkit-backdrop-filter: blur(12px);
     border-bottom: 1px solid var(--border);
     display: flex;
     align-items: center;
     justify-content: space-between;
     padding: 0 1.25rem;
     height: 3.75rem;
   }
   ```
2. **Nav Tab Buttons:**
   ```css
   .nav-tab-btn {
     display: inline-flex;
     align-items: center;
     gap: 0.45rem;
     padding: 0.45rem 0.85rem;
     border-radius: 0.5rem;
     font-size: 0.8rem;
     font-weight: 500;
     color: var(--muted-foreground);
     background: transparent;
     border: 1px solid transparent;
     cursor: pointer;
     transition: all 0.15s ease;
     user-select: none;
   }

   .nav-tab-btn:hover {
     color: var(--foreground);
     background: var(--muted);
   }

   .nav-tab-btn.active {
     color: var(--foreground);
     background: var(--card);
     border-color: var(--border);
     box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
     font-weight: 600;
   }
   ```
3. **Form Inputs, Selects & Sliders:**
   ```css
   input[type="text"],
   input[type="number"],
   input[type="password"],
   select,
   textarea {
     width: 100%;
     padding: 0.55rem 0.85rem;
     background: var(--card);
     border: 1px solid var(--input);
     border-radius: 0.5rem;
     color: var(--foreground);
     font-size: 0.85rem;
     outline: none;
     transition: border-color 0.15s ease, box-shadow 0.15s ease;
   }

   input:focus, select:focus, textarea:focus {
     border-color: var(--ring);
     box-shadow: 0 0 0 2px oklch(0.42 0.065 155 / 20%);
   }
   ```
4. **Light Mode High-Contrast Badges:**
   ```css
   .badge-emerald {
     background: oklch(0.42 0.065 155 / 12%);
     color: oklch(0.32 0.08 155);
     border-color: oklch(0.42 0.065 155 / 25%);
   }
   .badge-sky {
     background: oklch(0.50 0.12 230 / 12%);
     color: oklch(0.35 0.12 230);
     border-color: oklch(0.50 0.12 230 / 25%);
   }
   .badge-amber {
     background: oklch(0.55 0.12 75 / 12%);
     color: oklch(0.38 0.10 75);
     border-color: oklch(0.55 0.12 75 / 25%);
   }
   .badge-rose {
     background: oklch(0.58 0.16 28 / 12%);
     color: oklch(0.40 0.16 28);
     border-color: oklch(0.58 0.16 28 / 25%);
   }
   .badge-zinc {
     background: var(--secondary);
     color: var(--muted-foreground);
     border-color: var(--border);
   }
   ```
5. **Secondary Utilities & Modal Surfaces:**
   - Update `.btn-secondary` hover to `var(--accent)`.
   - Update `.modal-card` shadow to `0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)`.
   - Update `.bg-secondary/30` through `.bg-secondary/80` to derive cleanly from `oklch(0.96 0.008 140)`.

**Step 4: Run test to verify it passes**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/test_web_server.py::WebServerTests::test_light_mode_component_contrast_and_surfaces -v`
Expected: PASS (1 passed)

**Step 5: Commit**

```bash
git add hermes/src/web/static/style.css hermes/tests/test_web_server.py
git commit -m "style(web): tune light mode surfaces, inputs, nav buttons, and high-contrast badges"
```

---

### Task 4: Multi-Repo Verification & Field Gate Check

**Files:**
- Test: All suites across Hermes, Argus, and Janus

**Step 1: Run complete Hermes test suite**

Run: `/Users/kaalu/importante/hermes/.venv/bin/pytest /Users/kaalu/importante/hermes/tests/ -v`
Expected: All 160+ tests PASS without error.

**Step 2: Run Argus test suite**

Run: `/Users/kaalu/importante/argus/.venv/bin/pytest /Users/kaalu/importante/argus/tests/ -q`
Expected: 194 passed.

**Step 3: Run Janus test suite**

Run: `cd /Users/kaalu/importante/janus && npm test`
Expected: 562 passed.

**Step 4: Run static analysis and linting**

Run: `cd /Users/kaalu/importante/hermes && ruff check .`
Expected: All checks pass, 0 violations.

**Step 5: Verify rendered HTML with curl**

Start temporary test server or run Flask client test:
Run: `/Users/kaalu/importante/hermes/.venv/bin/python -c "from src.web.app import create_app; c = create_app().test_client(); r = c.get('/'); assert r.status_code == 200; print('Rendered HTML check PASSED')"`
Expected: `Rendered HTML check PASSED`

**Step 6: Commit and Push**

```bash
git status
git push origin feat/durability-offline-queue-and-secrets-hardening
```
