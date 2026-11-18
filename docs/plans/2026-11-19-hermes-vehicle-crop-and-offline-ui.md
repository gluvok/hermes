# Hermes: Vehicle Cropping Engine, Sidebar Removal & Offline Web UI Plan

> **Goal:** 
> 1. Implement vehicle bounding box cropping with percentage padding (top, bottom, left, right) on Hermes before transmitting vehicle images to Janus, falling back gracefully to uncropped frames.
> 2. Eliminate runtime Tailwind JavaScript (`tailwindcss.js`) from Hermes web console, replacing it with 100% offline pure CSS in `static/style.css`.
> 3. Remove the vertical sidebar and implement a clean, industrial top navigation header.

---

### Task 1: Vehicle Bounding Box Crop Function with Boundary Clamping
**Skill:** `@test-driven-development`

**Files:**
- Create: `hermes/tests/test_vehicle_crop.py`
- Create: `hermes/src/devices/crop.py`

**Step 1: Write unit tests for cropping logic**
- Test cropping a known 640x480 frame with box `(100, 100, 300, 300)` and 10% padding.
- Test edge boundary clamping: padding extending beyond image borders (e.g. `x1 - pad < 0` or `x2 + pad > width`) clamps safely to `0` and `width`.
- Test graceful fallback: passing `vehicle_box=None` or corrupt box returns the original uncropped JPEG bytes untouched.

**Step 2: Implement `crop_vehicle_frame()` in `hermes/src/devices/crop.py`**
- Use OpenCV (`cv2.imdecode` / `cv2.imencode`) to crop slices based on percentage offsets.
- Return JPEG bytes with quality 85.

**Step 3: Run test to verify it passes**
```bash
cd hermes && uv run pytest tests/test_vehicle_crop.py -v
```

---

### Task 2: Hermes Config & SQLite Persistence for Crop Padding
**Skill:** `@database-design`

**Files:**
- Modify: `hermes/src/config/constants.py`
- Modify: `hermes/src/config/client_config.py`
- Modify: `hermes/src/config/manager.py`
- Create: `hermes/tests/test_crop_config_persistence.py`

**Step 1: Add default padding constants**
- `DEFAULT_CROP_PAD_TOP: float = 10.0`
- `DEFAULT_CROP_PAD_BOTTOM: float = 10.0`
- `DEFAULT_CROP_PAD_LEFT: float = 15.0`
- `DEFAULT_CROP_PAD_RIGHT: float = 15.0`

**Step 2: Add getters and runtime overrides in `ConfigManager`**
- Add `crop_pad_top`, `crop_pad_bottom`, `crop_pad_left`, `crop_pad_right` properties to `ConfigManager` backed by SQLite `runtime_config`.

**Step 3: Verify persistence test**
```bash
cd hermes && uv run pytest tests/test_crop_config_persistence.py -v
```

---

### Task 3: Integration into Session Lifecycle & ANPR Pipeline
**Skill:** `@systematic-debugging`

**Files:**
- Modify: `hermes/src/integrations/anpr.py`
- Modify: `hermes/src/core/session.py`
- Create: `hermes/tests/test_crop_session_integration.py`

**Step 1: Update `anpr.py` to return `vehicle_box`**
- In `_extract_plate_from_dict(data)`, extract `vehicle_box: tuple[int, int, int, int] | None` from `results[0].get("vehicle_box")`.
- Propagate `vehicle_box` through `send_frame_to_anpr_server()` and `dispatch_anpr_batch()`.

**Step 2: Update `session.py` package finalization**
- When `_finalize_session_package()` prepares snapshots for the primary ANPR camera, call `crop_vehicle_frame(raw_bytes, best_vehicle_box, pad_top=..., pad_bottom=..., pad_left=..., pad_right=...)`.
- Save the cropped JPEG into `camera_snapshots["anpr_1"]`.

**Step 3: Run integration test**
```bash
cd hermes && uv run pytest tests/test_crop_session_integration.py -v
```

---

### Task 4: Zero-Dependency 100% Offline Static CSS (`style.css`)
**Skill:** `@frontend-patterns`

**Files:**
- Create: `hermes/src/web/static/style.css`

**Step 1: Write pure CSS stylesheet**
- Modern dark-theme palette (`#09090b` background, `#18181b` cards, `#27272a` borders, emerald/sky accents).
- Pure CSS component classes: `.top-nav`, `.nav-pill`, `.card`, `.badge`, `.btn-primary`, `.form-input`, `.slider-group`.
- 100% offline: zero `@import`, zero CDN fonts, zero JS runtime.

---

### Task 5: Web UI Transformation: Sidebar Removal & Top Navigation
**Skill:** `@senior-fullstack`

**Files:**
- Modify: `hermes/src/web/templates/index.html`

**Step 1: Remove sidebar and runtime Tailwind compiler**
- Remove `<script src="{{ url_for('static', filename='tailwindcss.js') }}"></script>`.
- Link `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">`.
- Delete `<aside id="main-sidebar">` and `#sidebar-backdrop`.

**Step 2: Add Top Navigation Bar**
- Clean top header containing Hermes logo, version, active status pill, and compact tab pills (`Overview`, `Cameras & Crop`, `Scale`, `Network`, `Config`).
- Add crop padding controls (sliders for Top, Bottom, Left, Right %) in the Cameras & Crop view.

---

### Task 6: Web API Endpoints & Input Validation for Crop Padding
**Skill:** `@api-patterns`

**Files:**
- Modify: `hermes/src/web/validation.py`
- Modify: `hermes/src/web/blueprints/api.py`
- Create: `hermes/tests/test_crop_api.py`

**Step 1: Add validation rules**
- Validate `crop_pad_top`, `crop_pad_bottom`, `crop_pad_left`, `crop_pad_right` in `validate_config_payload()` (must be numeric, between 0.0% and 100.0%).

**Step 2: Wire into `api.py`**
- Include padding values in `GET /api/config` response.
- Accept and persist padding values in `POST /api/config`.

**Step 3: Run API tests**
```bash
cd hermes && uv run pytest tests/test_crop_api.py -v
```

---

### Task 7: Comprehensive Verification & Regression Gate
**Skill:** `@verification-loop`

**Files:**
- Execute: `./scripts/verify-system-baseline.sh`
- Verify clean git status across `hermes`, `argus`, and `janus`.

**Step 1: Run all test suites**
- Hermes pytest suite (target: all passing).
- Argus pytest suite (target: all passing).
- Janus vitest suite (target: all passing).

**Step 2: Commit and push**
```bash
cd hermes
git add .
git commit -m "feat(crop): add vehicle bounding box cropping with padding, top navigation, and offline CSS"
git push origin feat/durability-offline-queue-and-secrets-hardening
```
