import unittest
from pathlib import Path


class TestMaintainerSheetTabs(unittest.TestCase):
    def test_maintainer_sheet_tabs_and_panels(self):
        root = Path(__file__).parent.parent
        template_file = root / "src" / "web" / "templates" / "index.html"
        self.assertTrue(template_file.exists(), "Missing index.html")

        html = template_file.read_text()

        # Categorized Maintainer Navigation Tabs
        self.assertIn('id="tab-btn-hw"', html, "Missing id='tab-btn-hw'")
        self.assertIn('id="tab-btn-cameras"', html, "Missing id='tab-btn-cameras'")
        self.assertIn('id="tab-btn-cloud"', html, "Missing id='tab-btn-cloud'")
        self.assertIn('id="tab-btn-telemetry"', html, "Missing id='tab-btn-telemetry'")

        # Diagnostic Tab Panels
        self.assertIn('id="tab-panel-hw"', html, "Missing id='tab-panel-hw'")
        self.assertIn('id="tab-panel-cameras"', html, "Missing id='tab-panel-cameras'")
        self.assertIn('id="tab-panel-cloud"', html, "Missing id='tab-panel-cloud'")
        self.assertIn('id="tab-panel-telemetry"', html, "Missing id='tab-panel-telemetry'")
