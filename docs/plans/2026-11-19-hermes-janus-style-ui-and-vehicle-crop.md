# Hermes Janus-Style UI Overhaul & Vehicle Crop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement OpenCV vehicle bounding box cropping with configurable percentage padding in Hermes edge sessions, persist crop padding in SQLite, remove the legacy sidebar in favor of a Janus-style industrial top navigation header, and provide 100% offline, zero-CDN CSS styling matching Janus's OKLCH zinc design system.

**Architecture:** 
1. Core vision pipeline decodes camera frames via OpenCV, extracts vehicle bounding boxes provided by Argus ANPR, calculates clamped percentage-padded coordinates, crops the vehicle, and encodes back to JPEG.
2. Runtime configuration parameters (`crop_pad_top`, `crop_pad_bottom`, `crop_pad_left`, `crop_pad_right`) persist in Hermes SQLite `runtime_config` and are modifiable via validated REST API endpoints (`GET/POST /api/config`).
3. Frontend architecture eliminates runtime JIT compilers (`tailwindcss.js`) and external CDNs, replacing them with a static, pre-compiled stylesheet (`src/web/static/style.css`) matching Janus design tokens (zinc-950 background, zinc-900 cards, emerald/sky status badges, and top-tier industrial navigation).

**Tech Stack:** Python 3.11+, Flask 3.1, OpenCV (`cv2`), SQLite3, Vanilla JavaScript (ES6+), Static CSS (OKLCH color mapping, zero runtime dependencies), Pytest.

---

### Task 1: OpenCV Vehicle Bounding Box Cropping Engine
**Skill:** `@test-driven-development`

**Files:**
- Create: `src/devices/crop.py`
- Test: `tests/test_vehicle_crop.py`

**Step 1: Write the failing test**

Write `tests/test_vehicle_crop.py`:
```python
from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.devices.crop import crop_vehicle_frame


def _create_synthetic_jpeg(width: int = 640, height: int = 480) -> bytes:
    """Create a synthetic solid colored image encoded as JPEG."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)  # Solid gray
    img[100:300, 100:300] = (0, 255, 0)  # Green box
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


def test_crop_vehicle_frame_with_padding():
    raw_jpeg = _create_synthetic_jpeg(640, 480)
    box = (100, 100, 300, 300)

    # 10% pad top/bottom = 20px -> height 240
    # 15% pad left/right = 30px -> width 260
    cropped_jpeg = crop_vehicle_frame(
        raw_jpeg,
        box=box,
        pad_top_pct=0.10,
        pad_bottom_pct=0.10,
        pad_left_pct=0.15,
        pad_right_pct=0.15,
    )

    assert cropped_jpeg != raw_jpeg
    nparr = np.frombuffer(cropped_jpeg, np.uint8)
    cropped_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert cropped_img is not None
    h, w = cropped_img.shape[:2]
    assert w == 260
    assert h == 240


def test_crop_boundary_clamping():
    raw_jpeg = _create_synthetic_jpeg(640, 480)
    box = (20, 20, 620, 460)

    cropped_jpeg = crop_vehicle_frame(
        raw_jpeg,
        box=box,
        pad_top_pct=0.20,
        pad_bottom_pct=0.20,
        pad_left_pct=0.20,
        pad_right_pct=0.20,
    )

    nparr = np.frombuffer(cropped_jpeg, np.uint8)
    cropped_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    assert cropped_img is not None
    h, w = cropped_img.shape[:2]
    assert w == 640
    assert h == 480


def test_crop_fallback_on_none_or_invalid_box():
    raw_jpeg = _create_synthetic_jpeg(640, 480)

    assert crop_vehicle_frame(raw_jpeg, box=None) == raw_jpeg
    assert crop_vehicle_frame(raw_jpeg, box=(300, 300, 100, 100)) == raw_jpeg
    assert crop_vehicle_frame(b"", box=(10, 10, 50, 50)) == b""
```

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --directory hermes pytest tests/test_vehicle_crop.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'src.devices.crop'` or `ImportError`.

**Step 3: Write minimal implementation**

Write `src/devices/crop.py`:
```python
"""crop.py — Vehicle Bounding Box Cropping with Percentage Padding."""

from __future__ import annotations

import logging
from typing import Sequence

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def crop_vehicle_frame(
    image_bytes: bytes,
    box: Sequence[int | float] | None,
    pad_top_pct: float = 0.10,
    pad_bottom_pct: float = 0.10,
    pad_left_pct: float = 0.15,
    pad_right_pct: float = 0.15,
) -> bytes:
    """
    Crops image to vehicle bounding box with percentage-based padding.

    :param image_bytes: Raw JPEG bytes of full camera frame.
    :param box: (x1, y1, x2, y2) bounding box coordinates.
    :param pad_top_pct: Fraction of box height to pad above (e.g. 0.10 = 10%).
    :param pad_bottom_pct: Fraction of box height to pad below.
    :param pad_left_pct: Fraction of box width to pad on the left.
    :param pad_right_pct: Fraction of box width to pad on the right.
    :return: Cropped JPEG bytes, or original image_bytes if box is None/invalid.
    """
    if not image_bytes or not box or len(box) < 4:
        return image_bytes

    try:
        x1, y1, x2, y2 = (int(v) for v in box[:4])
        if x2 <= x1 or y2 <= y1:
            logger.debug("[Crop] Invalid bounding box coordinates: %s", box)
            return image_bytes

        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return image_bytes

        img_h, img_w = frame.shape[:2]
        bw = x2 - x1
        bh = y2 - y1

        pad_l = int(bw * max(0.0, pad_left_pct))
        pad_r = int(bw * max(0.0, pad_right_pct))
        pad_t = int(bh * max(0.0, pad_top_pct))
        pad_b = int(bh * max(0.0, pad_bottom_pct))

        crop_x1 = max(0, x1 - pad_l)
        crop_y1 = max(0, y1 - pad_t)
        crop_x2 = min(img_w, x2 + pad_r)
        crop_y2 = min(img_h, y2 + pad_b)

        if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
            return image_bytes

        cropped = frame[crop_y1:crop_y2, crop_x1:crop_x2]
        success, encoded = cv2.imencode(
            ".jpg", cropped, [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        if success:
            return encoded.tobytes()
        return image_bytes
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Crop] Exception while cropping vehicle frame: %s", exc)
        return image_bytes
```

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --directory hermes pytest tests/test_vehicle_crop.py -v
```
Expected: `3 passed in 0.25s`.

**Step 5: Commit**

```bash
git -C hermes add src/devices/crop.py tests/test_vehicle_crop.py
git -C hermes commit -m "feat(vision): add vehicle bounding box cropping with percentage padding"
```

---

### Task 2: Dynamic Crop Padding Configuration Persistence in SQLite
**Skill:** `@database-design`

**Files:**
- Modify: `src/config/constants.py`
- Modify: `src/config/runtime.py`
- Modify: `src/config/manager.py`
- Modify: `src/config/client_config.py`
- Test: `tests/test_crop_config_persistence.py`

**Step 1: Write the failing test**

Write `tests/test_crop_config_persistence.py`:
```python
from __future__ import annotations

import tempfile
from src.config.manager import ConfigManager


def test_crop_padding_defaults():
    with tempfile.NamedTemporaryFile() as tmp:
        cfg = ConfigManager(db_path=tmp.name)
        assert cfg.crop_pad_top == 10.0
        assert cfg.crop_pad_bottom == 10.0
        assert cfg.crop_pad_left == 15.0
        assert cfg.crop_pad_right == 15.0


def test_crop_padding_persistence():
    with tempfile.NamedTemporaryFile() as tmp:
        cfg = ConfigManager(db_path=tmp.name)
        cfg.update_system_config(
            crop_pad_top=12.5,
            crop_pad_bottom=18.0,
            crop_pad_left=22.0,
            crop_pad_right=25.0,
        )

        # Reload from the same SQLite file to simulate reboot
        cfg_reloaded = ConfigManager(db_path=tmp.name)
        assert cfg_reloaded.crop_pad_top == 12.5
        assert cfg_reloaded.crop_pad_bottom == 18.0
        assert cfg_reloaded.crop_pad_left == 22.0
        assert cfg_reloaded.crop_pad_right == 25.0
```

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --directory hermes pytest tests/test_crop_config_persistence.py -v
```
Expected: FAIL with `AttributeError: 'ConfigManager' object has no attribute 'crop_pad_top'`.

**Step 3: Write minimal implementation**

1. In `src/config/constants.py`, add default percentage constants:
```python
DEFAULT_CROP_PAD_TOP: float = 10.0
DEFAULT_CROP_PAD_BOTTOM: float = 10.0
DEFAULT_CROP_PAD_LEFT: float = 15.0
DEFAULT_CROP_PAD_RIGHT: float = 15.0
```

2. In `src/config/runtime.py`, add properties and update logic:
```python
@property
def crop_pad_top(self) -> float:
    return float(self.get("crop_pad_top", 10.0))

@property
def crop_pad_bottom(self) -> float:
    return float(self.get("crop_pad_bottom", 10.0))

@property
def crop_pad_left(self) -> float:
    return float(self.get("crop_pad_left", 15.0))

@property
def crop_pad_right(self) -> float:
    return float(self.get("crop_pad_right", 15.0))
```

3. In `src/config/manager.py`, expose properties and persistence in SQLite:
```python
@property
def crop_pad_top(self) -> float:
    return float(self.runtime.crop_pad_top)

@property
def crop_pad_bottom(self) -> float:
    return float(self.runtime.crop_pad_bottom)

@property
def crop_pad_left(self) -> float:
    return float(self.runtime.crop_pad_left)

@property
def crop_pad_right(self) -> float:
    return float(self.runtime.crop_pad_right)
```
And inside `update_system_config(**kwargs)`:
```python
for key in ("crop_pad_top", "crop_pad_bottom", "crop_pad_left", "crop_pad_right"):
    if key in kwargs and kwargs[key] is not None:
        self.set_runtime(key, float(kwargs[key]))
```

4. In `src/config/client_config.py`, include crop padding keys in exported config dictionary.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --directory hermes pytest tests/test_crop_config_persistence.py -v
```
Expected: `2 passed in 0.12s`.

**Step 5: Commit**

```bash
git -C hermes add src/config/ tests/test_crop_config_persistence.py
git -C hermes commit -m "feat(config): persist crop padding percentages in SQLite store"
```

---

### Task 3: ANPR Integration & Session Packaging Pipeline
**Skill:** `@systematic-debugging`

**Files:**
- Modify: `src/integrations/anpr.py`
- Modify: `src/core/session.py`
- Test: `tests/test_crop_session_integration.py`

**Step 1: Write the failing test**

Write `tests/test_crop_session_integration.py`:
```python
import unittest
import cv2
import numpy as np

from src.core.session import WeighbridgeSessionManager, SessionPhase
from src.config import config


class TestCropSessionIntegration(unittest.TestCase):
    def setUp(self):
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        img[100:300, 100:300] = [0, 255, 0]
        _, enc = cv2.imencode(".jpg", img)
        self.sample_jpeg = enc.tobytes()

    def test_record_anpr_result_stores_vehicle_box(self):
        mgr = WeighbridgeSessionManager()
        mgr.session_id = "TEST_SESS_1"
        mgr.phase = SessionPhase.PHASE_STABILIZING

        mgr.record_anpr_result(
            "TEST_SESS_1", 1, "MH12AB1234", "SUCCESS", vehicle_box=(100, 100, 300, 300)
        )
        self.assertEqual(mgr._last_vehicle_box, (100, 100, 300, 300))

    def test_finalize_package_crops_anpr_1_with_configured_padding(self):
        mgr = WeighbridgeSessionManager()
        mgr.session_id = "TEST_SESS_2"
        mgr.phase = SessionPhase.PHASE_STABILIZING
        mgr.stable_weight = 12500.0

        mgr._anpr_frame_buffers[1] = [self.sample_jpeg]
        mgr._anpr_plates.append("KA01CD5678")
        mgr._last_vehicle_box = (100, 100, 300, 300)

        # 0% padding produces exact 200x200 crop
        config.runtime.update_system(
            crop_pad_top=0.0,
            crop_pad_bottom=0.0,
            crop_pad_left=0.0,
            crop_pad_right=0.0,
        )
        try:
            pkg = mgr._finalize_session_package()
        finally:
            config.runtime.update_system(
                crop_pad_top=10.0,
                crop_pad_bottom=10.0,
                crop_pad_left=15.0,
                crop_pad_right=15.0,
            )

        cropped_bytes = pkg["camera_snapshots"]["anpr_1"]
        self.assertIsNotNone(cropped_bytes)

        arr = np.frombuffer(cropped_bytes, dtype=np.uint8)
        dec = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = dec.shape[:2]
        self.assertEqual((w, h), (200, 200))

    def test_finalize_package_falls_back_when_no_vehicle_box(self):
        mgr = WeighbridgeSessionManager()
        mgr.session_id = "TEST_SESS_3"
        mgr.phase = SessionPhase.PHASE_STABILIZING
        mgr.stable_weight = 8000.0

        mgr._anpr_frame_buffers[1] = [self.sample_jpeg]
        mgr._last_vehicle_box = None

        pkg = mgr._finalize_session_package()
        out_bytes = pkg["camera_snapshots"]["anpr_1"]
        self.assertIsNotNone(out_bytes)

        arr = np.frombuffer(out_bytes, dtype=np.uint8)
        dec = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = dec.shape[:2]
        self.assertEqual((w, h), (400, 400))
```

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --directory hermes pytest tests/test_crop_session_integration.py -v
```
Expected: FAIL with `TypeError: record_anpr_result() got an unexpected keyword argument 'vehicle_box'`.

**Step 3: Write minimal implementation**

1. In `src/integrations/anpr.py`, update `_extract_plate_from_dict`:
```python
vehicle_box = first.get("vehicle_box")
return plate_text, status, vehicle_box
```
And propagate `vehicle_box` through `on_plate_detected(session_id, camera_index, plate, status, vehicle_box)`.

2. In `src/core/session.py`, update `record_anpr_result` and `_finalize_session_package`:
```python
def record_anpr_result(
    self, session_id: str, camera_index: int, plate: str, status: str, vehicle_box: Sequence[int | float] | None = None
) -> None:
    ...
    if vehicle_box is not None:
        self._last_vehicle_box = tuple(vehicle_box)
```
And in `_finalize_session_package`:
```python
from src.devices.crop import crop_vehicle_frame

raw_anpr = snapshots.get("anpr_1")
if raw_anpr and self._last_vehicle_box:
    snapshots["anpr_1"] = crop_vehicle_frame(
        raw_anpr,
        box=self._last_vehicle_box,
        pad_top_pct=config.crop_pad_top / 100.0,
        pad_bottom_pct=config.crop_pad_bottom / 100.0,
        pad_left_pct=config.crop_pad_left / 100.0,
        pad_right_pct=config.crop_pad_right / 100.0,
    )
```

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --directory hermes pytest tests/test_crop_session_integration.py -v
```
Expected: `3 passed in 0.38s`.

**Step 5: Commit**

```bash
git -C hermes add src/integrations/anpr.py src/core/session.py tests/test_crop_session_integration.py
git -C hermes commit -m "feat(session): crop primary vehicle snapshot using argus vehicle_box and padding"
```

---

### Task 4: REST API Validation & Dynamic Configuration Endpoints
**Skill:** `@api-patterns`

**Files:**
- Modify: `src/web/validation.py`
- Modify: `src/web/blueprints/api.py`
- Test: `tests/test_crop_api.py`

**Step 1: Write the failing test**

Write `tests/test_crop_api.py`:
```python
import unittest
from src.web.app import create_app
from src.config import config
from src.web.auth import create_session_token


class TestCropApi(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.token = create_session_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def test_get_config_includes_crop_padding(self):
        res = self.client.get("/api/config", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("crop_pad_top", data)
        self.assertIn("crop_pad_bottom", data)
        self.assertIn("crop_pad_left", data)
        self.assertIn("crop_pad_right", data)

    def test_post_config_updates_crop_padding(self):
        payload = {
            "crop_pad_top": 12.0,
            "crop_pad_bottom": 14.5,
            "crop_pad_left": 18.0,
            "crop_pad_right": 20.0,
        }
        res = self.client.post("/api/config", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        self.assertEqual(config.crop_pad_top, 12.0)
        self.assertEqual(config.crop_pad_bottom, 14.5)
        self.assertEqual(config.crop_pad_left, 18.0)
        self.assertEqual(config.crop_pad_right, 20.0)

    def test_post_config_rejects_out_of_range_padding(self):
        payload = {"crop_pad_top": 150.0}
        res = self.client.post("/api/config", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("between 0.0 and 100.0 percent", data.get("error", ""))
```

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --directory hermes pytest tests/test_crop_api.py -v
```
Expected: FAIL with missing fields or validation error.

**Step 3: Write minimal implementation**

1. In `src/web/validation.py`, validate percentage bounds [0.0, 100.0]:
```python
for pad_key in ("crop_pad_top", "crop_pad_bottom", "crop_pad_left", "crop_pad_right"):
    if pad_key in data:
        try:
            val = float(data[pad_key])
            if not (0.0 <= val <= 100.0):
                return False, f"{pad_key} must be between 0.0 and 100.0 percent"
            validated[pad_key] = val
        except (ValueError, TypeError):
            return False, f"{pad_key} must be a valid float"
```

2. In `src/web/blueprints/api.py`:
- In `get_config()`: include `crop_pad_top`, `crop_pad_bottom`, `crop_pad_left`, `crop_pad_right` in payload response.
- In `save_config()`: pass validated crop padding keys into `config.update_system_config(...)`.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --directory hermes pytest tests/test_crop_api.py -v
```
Expected: `3 passed in 0.22s`.

**Step 5: Commit**

```bash
git -C hermes add src/web/validation.py src/web/blueprints/api.py tests/test_crop_api.py
git -C hermes commit -m "feat(api): expose and validate crop padding in /api/config"
```

---

### Task 5: Janus Design System CSS Architecture (Zero-Dependency Offline Static Stylesheet)
**Skill:** `@senior-frontend`

**Files:**
- Create: `src/web/static/style.css`
- Test: `tests/test_web_server.py`

**Step 1: Write the failing test**

In `tests/test_web_server.py`, add assertions verifying zero CDN scripts and existence of static style link:
```python
def test_static_stylesheet_linked_offline(self):
    res = self.client.get("/")
    html = res.get_data(as_text=True)
    self.assertIn('href="/static/style.css"', html)
    self.assertNotIn("tailwindcss.com", html)
    self.assertNotIn("unpkg.com", html)
    self.assertNotIn("cdn.jsdelivr.net", html)

    css_res = self.client.get("/static/style.css")
    self.assertEqual(css_res.status_code, 200)
    self.assertIn("--bg-base: #09090b", css_res.get_data(as_text=True))
```

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --directory hermes pytest tests/test_web_server.py -k test_static_stylesheet_linked_offline -v
```
Expected: FAIL if `style.css` is missing or content is absent.

**Step 3: Write minimal implementation**

Write `src/web/static/style.css` matching Janus tokens:
```css
/**
 * Hermes Industrial Edge Web Console Stylesheet
 * 100% Zero-Dependency, Offline-First Static CSS
 * Tokens mapped to Janus Dark Mode Architecture
 */

:root {
  --bg-base: #09090b;
  --bg-card: #121215;
  --bg-card-hover: #18181b;
  --bg-muted: #1c1c21;
  --bg-accent: #27272a;
  --border: #27272a;
  --border-light: #3f3f46;
  --text-main: #fafafa;
  --text-muted: #a1a1aa;
  --text-dim: #71717a;
  --accent-sky: #38bdf8;
  --accent-emerald: #34d399;
  --accent-amber: #fbbf24;
  --accent-rose: #f87171;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  background-color: var(--bg-base);
  color: var(--text-main);
  font-family: var(--font-sans);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* Janus Industrial Header */
.top-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background-color: rgba(9, 9, 11, 0.96);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.25rem;
  height: 3.75rem;
}

.top-nav-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  min-width: 0;
}

.brand-badge {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  text-decoration: none;
  color: var(--text-main);
}

.brand-logo {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.5rem;
  background: #18181b;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-tabs-container {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  overflow-x: auto;
}

.nav-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.85rem;
  border-radius: 0.5rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-tab-btn:hover {
  color: var(--text-main);
  background: var(--bg-card);
}

.nav-tab-btn.active {
  color: var(--text-main);
  background: var(--bg-card);
  border-color: var(--border-light);
}

.top-nav-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* Layout & Cards */
.main-content {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Grid & Flex Utilities */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.gap-2 { gap: 0.5rem; }
.gap-4 { gap: 1rem; }
.gap-6 { gap: 1.5rem; }
.flex { display: flex; }
.inline-flex { display: inline-flex; }
.flex-col { flex-direction: column; }
.flex-1 { flex: 1 1 0%; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.space-y-2 > * + * { margin-top: 0.5rem; }
.space-y-4 > * + * { margin-top: 1rem; }

/* Status Badges */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
  border: 1px solid transparent;
}
.badge-emerald { background: rgba(52, 211, 153, 0.12); color: var(--accent-emerald); border-color: rgba(52, 211, 153, 0.25); }
.badge-sky { background: rgba(56, 189, 248, 0.12); color: var(--accent-sky); border-color: rgba(56, 189, 248, 0.25); }
.badge-amber { background: rgba(251, 191, 36, 0.12); color: var(--accent-amber); border-color: rgba(251, 191, 36, 0.25); }
.badge-rose { background: rgba(248, 113, 113, 0.12); color: var(--accent-rose); border-color: rgba(248, 113, 113, 0.25); }
.badge-zinc { background: var(--bg-accent); color: var(--text-muted); border-color: var(--border-light); }

/* Buttons & Inputs */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.55rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn-primary { background: var(--accent-sky); color: #09090b; font-weight: 700; }
.btn-secondary { background: var(--bg-muted); color: var(--text-main); border-color: var(--border); }
.btn-danger { background: rgba(248, 113, 113, 0.15); color: var(--accent-rose); border-color: rgba(248, 113, 113, 0.3); }

input[type="text"], input[type="number"], select {
  width: 100%;
  padding: 0.55rem 0.85rem;
  background: var(--bg-base);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-main);
  font-size: 0.85rem;
  outline: none;
}
input:focus, select:focus {
  border-color: var(--accent-sky);
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
}

/* Range Sliders */
.slider-container { display: flex; align-items: center; gap: 0.75rem; }
input[type="range"] { flex: 1; accent-color: var(--accent-sky); cursor: pointer; }

/* Typography */
.text-xs { font-size: 0.72rem; }
.text-sm { font-size: 0.82rem; }
.text-base { font-size: 0.92rem; }
.text-xl { font-size: 1.25rem; }
.font-bold { font-weight: 700; }
.font-mono { font-family: var(--font-mono); }
.text-emerald-400 { color: var(--accent-emerald); }
.text-sky-400 { color: var(--accent-sky); }
.text-amber-400 { color: var(--accent-amber); }
.text-rose-400 { color: var(--accent-rose); }
.hidden { display: none !important; }
```

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --directory hermes pytest tests/test_web_server.py -k test_static_stylesheet_linked_offline -v
```
Expected: `1 passed in 0.18s`.

**Step 5: Commit**

```bash
git -C hermes add src/web/static/style.css tests/test_web_server.py
git -C hermes commit -m "feat(web): add offline-first static css matching janus design system"
```

---

### Task 6: Modern Janus-Style Header & Tab Navigation in Web Console (`index.html`)
**Skill:** `@clean-code`

**Files:**
- Modify: `src/web/templates/index.html`
- Test: `tests/test_web_server.py`

**Step 1: Write the failing test**

In `tests/test_web_server.py`:
```python
def test_janus_navigation_elements_present_and_sidebar_removed(self):
    res = self.client.get("/")
    html = res.get_data(as_text=True)
    # Ensure legacy sidebar is deleted
    self.assertNotIn('id="main-sidebar"', html)
    # Ensure top nav bar and tabs exist
    self.assertIn('class="top-nav"', html)
    self.assertIn('id="nav-item-overview"', html)
    self.assertIn('id="nav-item-anpr"', html)
    self.assertIn('id="nav-item-scale"', html)
    # Ensure crop padding slider controls exist
    self.assertIn('id="crop_pad_top_slider"', html)
    self.assertIn('id="crop_pad_bottom_slider"', html)
    self.assertIn('id="crop_pad_left_slider"', html)
    self.assertIn('id="crop_pad_right_slider"', html)
```

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --directory hermes pytest tests/test_web_server.py -k test_janus_navigation_elements_present -v
```
Expected: FAIL if legacy sidebar is present or sliders missing.

**Step 3: Write minimal implementation**

1. In `src/web/templates/index.html`:
- Delete `#main-sidebar` element entirely.
- Add `<header class="top-nav">` with:
  - Brand identity: Luvok Hermes logo + `EDGE ONLINE` emerald badge.
  - Center tabs: Overview, Scale Indicator, Cameras & Crop, Cloud Transfer, Telemetry Logs, System Config, Wi-Fi Setup.
  - Right telemetry: Live Weight badge (`0 kg`), Sync queue status (`0 Pending`), and Admin Lock button.
- In `#view-anpr` (Cameras tab), add the **Vehicle Crop & Bounding Box Framing** card:
  - Interactive percentage sliders:
    - Top Padding (0% to 50%, step 1%, default 10%)
    - Bottom Padding (0% to 50%, step 1%, default 10%)
    - Left Padding (0% to 50%, step 1%, default 15%)
    - Right Padding (0% to 50%, step 1%, default 15%)
  - Visual wireframe container displaying before/after crop bounding box representation.
  - Live value updates synchronized with `POST /api/config`.

2. Update `switchTab(tabId)` in `index.html` to toggle `.active` class on `.nav-tab-btn`.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --directory hermes pytest tests/test_web_server.py -v
```
Expected: `24 passed in 1.45s`.

**Step 5: Commit**

```bash
git -C hermes add src/web/templates/index.html tests/test_web_server.py
git -C hermes commit -m "feat(ui): implement janus top navigation header and vehicle crop sliders"
```

---

### Task 7: Tri-Repo End-to-End Regression & Field Verification Gate
**Skill:** `@verification-loop`

**Files:**
- Test: Full test suites of `hermes`, `argus`, and `janus`

**Step 1: Write the failing test**

Verify that all three repositories maintain zero type errors, zero lint warnings, and 100% test pass rates across their integration contracts.

**Step 2: Run test to verify baseline**

Run:
```bash
uv run --directory argus pytest
npm --prefix janus run test
uv run --directory hermes pytest
```
Expected: All suites must pass cleanly.

**Step 3: Execute full verification loop**

1. Execute Hermes test suite:
```bash
uv run --directory hermes pytest -v
```
Expected: 158/158 tests passing.

2. Execute Argus test suite:
```bash
uv run --directory argus pytest -q
```
Expected: 194/194 tests passing.

3. Execute Janus test suite:
```bash
npm --prefix janus run test
```
Expected: 562/562 tests passing.

4. Check live web server endpoint on port 8080:
```bash
curl -s http://127.0.0.1:8080/ | grep -E "top-nav|style.css|crop_pad"
```
Expected: All elements present in served HTML.

**Step 4: Run verification to ensure green across all repos**

Confirm zero failures, no uncommitted unstaged modifications, and verify offline capability.

**Step 5: Commit**

```bash
git -C hermes status
git -C hermes push origin feat/durability-offline-queue-and-secrets-hardening
```

---
