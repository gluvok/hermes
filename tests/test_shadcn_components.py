import unittest
from pathlib import Path


class TestShadcnComponents(unittest.TestCase):
    def test_shadcn_component_sources_and_docs(self):
        root = Path(__file__).parent.parent
        ui_dir = root / "src" / "web" / "frontend" / "components" / "ui"
        kiosk_dir = root / "src" / "web" / "frontend" / "components" / "kiosk"
        docs_dir = root / "docs" / "shadcn"

        # Verify all UI components exist
        required_ui = ["card.tsx", "badge.tsx", "button.tsx", "tabs.tsx", "slider.tsx", "dialog.tsx"]
        for ui in required_ui:
            self.assertTrue((ui_dir / ui).exists(), f"Missing {ui} in {ui_dir}")

        # Verify kiosk dual-console components exist
        self.assertTrue((kiosk_dir / "operator-hud.tsx").exists(), "Missing operator-hud.tsx")
        self.assertTrue((kiosk_dir / "developer-console.tsx").exists(), "Missing developer-console.tsx")
        self.assertTrue((kiosk_dir / "console-mode-switcher.tsx").exists(), "Missing console-mode-switcher.tsx")

        # Verify page.tsx exists
        page_file = root / "src" / "web" / "frontend" / "app" / "page.tsx"
        self.assertTrue(page_file.exists(), "Missing page.tsx")

        # Verify matching documentation in docs/shadcn/ for each UI component
        for ui in required_ui:
            base_name = ui.replace(".tsx", ".md")
            self.assertTrue((docs_dir / base_name).exists(), f"Missing doc for {base_name}")

    def test_maintainer_sheet_and_minimalist_page(self):
        root = Path(__file__).parent.parent
        kiosk_dir = root / "src" / "web" / "frontend" / "components" / "kiosk"
        page_file = root / "src" / "web" / "frontend" / "app" / "page.tsx"

        self.assertTrue((kiosk_dir / "maintainer-sheet.tsx").exists(), "Missing maintainer-sheet.tsx")
        page_content = page_file.read_text()
        self.assertIn("MaintainerSheet", page_content)
        self.assertIn("OperatorHUD", page_content)

