import unittest
from pathlib import Path


class TestDeployConfig(unittest.TestCase):
    def test_production_docker_compose_configuration(self):
        root = Path(__file__).parent.parent
        compose_file = root / "deploy" / "docker-compose.prod.yml"
        self.assertTrue(compose_file.exists(), "Missing docker-compose.prod.yml")

        content = compose_file.read_text()

        # Check required services
        self.assertIn("hermes:", content)
        self.assertIn("argus:", content)
        self.assertIn("watchtower:", content)

        # Hermes must have stop_grace_period >= 30s for safe RS232 draining
        self.assertIn("stop_grace_period: 30s", content)

        # Serial device mapping for Raspberry Pi UART
        self.assertIn("/dev/ttyAMA0:/dev/ttyAMA0", content)

        # Watchtower auto-updater configuration
        self.assertIn("WATCHTOWER_CLEANUP=true", content)
        self.assertIn("WATCHTOWER_INCLUDE_STOPPED=true", content)

    def test_deploy_script_syntax(self):
        root = Path(__file__).parent.parent
        deploy_sh = root / "deploy" / "deploy_pi.sh"
        self.assertTrue(deploy_sh.exists(), "Missing deploy_pi.sh")
        content = deploy_sh.read_text()
        self.assertIn("#!/usr/bin/env bash", content)
        self.assertIn("docker compose -f", content)

    def test_release_edge_workflow_exists(self):
        root = Path(__file__).parent.parent
        workflow_file = root / ".github" / "workflows" / "release-edge.yml"
        self.assertTrue(workflow_file.exists(), "Missing release-edge.yml")
        content = workflow_file.read_text()
        self.assertIn("name:", content)
        self.assertIn("docker/build-push-action", content)
