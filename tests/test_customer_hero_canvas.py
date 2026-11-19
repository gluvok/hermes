import unittest
from pathlib import Path


class TestCustomerHeroCanvas(unittest.TestCase):
    def test_customer_hero_canvas_elements(self):
        root = Path(__file__).parent.parent
        template_file = root / "src" / "web" / "templates" / "index.html"
        self.assertTrue(template_file.exists(), "Missing index.html")

        html = template_file.read_text()

        # 60/40 Split Hero layout panes
        self.assertIn('id="hero-scale-pane"', html, "Missing id='hero-scale-pane'")
        self.assertIn('id="hero-camera-pane"', html, "Missing id='hero-camera-pane'")

        # Serial telemetry weight readout & stability pill
        self.assertIn('id="live-weight-display"', html, "Missing id='live-weight-display'")
        self.assertIn('id="weight-stability-pill"', html, "Missing id='weight-stability-pill'")

        # Vehicle overhead framing & ANPR recognized badge
        self.assertIn('id="anpr-plate-hero-badge"', html, "Missing id='anpr-plate-hero-badge'")

        # Preserved core hooks for telemetry and polling
        self.assertIn('id="ov-weight"', html, "Missing id='ov-weight'")
        self.assertIn('id="scale-state-detail"', html, "Missing id='scale-state-detail'")
        self.assertIn('id="ov-anpr-plate"', html, "Missing id='ov-anpr-plate'")
