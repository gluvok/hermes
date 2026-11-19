import unittest
from pathlib import Path


class TestTouchActionBar(unittest.TestCase):
    def test_touch_action_bar_and_dialog_elements(self):
        root = Path(__file__).parent.parent
        template_file = root / "src" / "web" / "templates" / "index.html"
        self.assertTrue(template_file.exists(), "Missing index.html")

        html = template_file.read_text()

        # Touch-optimized action bar (48px hit targets for gloved kiosk use)
        self.assertIn('id="touch-action-bar"', html, "Missing id='touch-action-bar'")
        self.assertIn('id="btn-quick-edit-plate"', html, "Missing id='btn-quick-edit-plate'")
        self.assertIn('id="btn-quick-print-slip"', html, "Missing id='btn-quick-print-slip'")
        self.assertIn('min-h-[48px]', html, "Missing min-h-[48px] touch target class")

        # Accessible plate override dialog (Shadcn style modal)
        self.assertIn('id="plate-override-dialog"', html, "Missing id='plate-override-dialog'")
        self.assertIn('id="override-plate-input"', html, "Missing id='override-plate-input'")
        self.assertIn('id="btn-confirm-plate-override"', html, "Missing id='btn-confirm-plate-override'")
        self.assertIn('id="btn-cancel-plate-override"', html, "Missing id='btn-cancel-plate-override'")
