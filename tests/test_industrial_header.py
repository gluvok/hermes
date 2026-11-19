import unittest
from pathlib import Path


class TestIndustrialHeader(unittest.TestCase):
    def test_industrial_header_elements_and_structure(self):
        root = Path(__file__).parent.parent
        template_file = root / "src" / "web" / "templates" / "index.html"
        self.assertTrue(template_file.exists(), "Missing index.html")

        html = template_file.read_text()

        # Clean 56px industrial header container
        self.assertIn('id="industrial-header"', html, "Missing id='industrial-header'")

        # Station metadata badge (Station ID / Lane info)
        self.assertIn('id="station-meta-badge"', html, "Missing id='station-meta-badge'")

        # Single aggregated hardware status beacon dot
        self.assertIn('id="hw-status-dot"', html, "Missing id='hw-status-dot'")

        # Non-intrusive maintainer drawer trigger
        self.assertIn('id="btn-open-maintainer-sheet"', html, "Missing id='btn-open-maintainer-sheet'")
