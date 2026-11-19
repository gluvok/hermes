import json
import unittest
from pathlib import Path


class TestFrontendScaffold(unittest.TestCase):
    def test_nextjs_frontend_configuration(self):
        root = Path(__file__).parent.parent
        fe_dir = root / "src" / "web" / "frontend"

        # Package.json exists and contains Next.js + shadcn dependencies
        pkg_file = fe_dir / "package.json"
        self.assertTrue(pkg_file.exists(), "Missing frontend/package.json")
        with open(pkg_file) as f:
            pkg = json.load(f)
        self.assertIn("next", pkg.get("dependencies", {}))
        self.assertIn("lucide-react", pkg.get("dependencies", {}))

        # components.json exists with Radix + Tailwind setup
        comp_file = fe_dir / "components.json"
        self.assertTrue(comp_file.exists(), "Missing components.json")

        # globals.css contains Janus OKLCH color palette and industrial tokens
        css_file = fe_dir / "app" / "globals.css"
        self.assertTrue(css_file.exists())
        css_content = css_file.read_text()
        self.assertIn("oklch(0.145 0.012 155)", css_content)
        self.assertIn("oklch(0.76 0.055 155)", css_content)
        self.assertIn("#0c1014", css_content.lower(), "Missing industrial slate base (#0c1014) in globals.css")
        self.assertIn("tabular-nums", css_content, "Missing tabular-nums in globals.css")

        # page.tsx contains tabular numbers for serial telemetry
        page_file = fe_dir / "app" / "page.tsx"
        self.assertTrue(page_file.exists())
        page_content = page_file.read_text()
        self.assertIn("tabular-nums", page_content, "Missing tabular-nums in page.tsx")

        # api-client.ts exists and implements fetchers
        client_file = fe_dir / "lib" / "api-client.ts"
        self.assertTrue(client_file.exists(), "Missing api-client.ts")
        client_content = client_file.read_text()
        self.assertIn("/api/status", client_content)
        self.assertIn("/api/config", client_content)

        # GitHub workflow for building frontend
        workflow = root / ".github" / "workflows" / "build-frontend.yml"
        self.assertTrue(workflow.exists(), "Missing build-frontend.yml")
