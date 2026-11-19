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
