import json
import unittest
from pathlib import Path


class TestShadcnDocsAndSkill(unittest.TestCase):
    def test_shadcn_skill_and_docs_structure(self):
        root = Path(__file__).parent.parent

        # Verify shadcn skill exists in skills-lock
        skills_lock_file = root / "skills-lock.json"
        self.assertTrue(skills_lock_file.exists(), f"Missing {skills_lock_file}")
        with open(skills_lock_file, "r") as f:
            lock_data = json.load(f)
        self.assertIn("skills", lock_data)
        self.assertIn("shadcn", lock_data["skills"])

        # Verify shadcn skill file exists
        skill_file = root / ".agents" / "skills" / "shadcn" / "SKILL.md"
        self.assertTrue(skill_file.exists(), f"Missing {skill_file}")

        # Verify docs/shadcn directory exists
        docs_dir = root / "docs" / "shadcn"
        self.assertTrue(docs_dir.is_dir(), f"Missing {docs_dir}")
        self.assertTrue((docs_dir / "README.md").exists(), "Missing README.md in docs/shadcn")

        # Verify core component docs exist
        required_components = ["card", "badge", "button", "tabs", "slider", "dialog"]
        for comp in required_components:
            doc_file = docs_dir / f"{comp}.md"
            self.assertTrue(doc_file.exists(), f"Missing doc for component: {comp}")
            content = doc_file.read_text()
            self.assertIn(f"# {comp.capitalize()}", content)
            self.assertIn("## Usage", content)
