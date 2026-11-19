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
