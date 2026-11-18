import os
import tempfile
import unittest

from src.core import wifi_vault


class TestWifiVault(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_hermes.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_retrieve_wifi_password(self):
        wifi_vault.save_wifi_network("Plant_5G", "SecretPass123", db_path=self.db_path)
        pwd = wifi_vault.get_wifi_password("Plant_5G", db_path=self.db_path)
        self.assertEqual(pwd, "SecretPass123")
        self.assertIsNone(
            wifi_vault.get_wifi_password("NonExistent", db_path=self.db_path)
        )

    def test_get_saved_wifi_networks_masks_passwords(self):
        wifi_vault.save_wifi_network("Net_A", "PassA", db_path=self.db_path)
        wifi_vault.save_wifi_network("Net_B", "PassB", db_path=self.db_path)

        networks = wifi_vault.get_saved_wifi_networks(db_path=self.db_path)
        self.assertEqual(len(networks), 2)
        ssids = [n["ssid"] for n in networks]
        self.assertIn("Net_A", ssids)
        self.assertIn("Net_B", ssids)
        for net in networks:
            self.assertNotIn("password", net)
            self.assertIn("created_at", net)
            self.assertIn("last_connected_at", net)

    def test_save_wifi_network_upsert_updates_password(self):
        wifi_vault.save_wifi_network("Factory_WiFi", "OldPass", db_path=self.db_path)
        self.assertEqual(
            wifi_vault.get_wifi_password("Factory_WiFi", db_path=self.db_path),
            "OldPass",
        )

        wifi_vault.save_wifi_network("Factory_WiFi", "NewPass", db_path=self.db_path)
        self.assertEqual(
            wifi_vault.get_wifi_password("Factory_WiFi", db_path=self.db_path),
            "NewPass",
        )

    def test_delete_and_clear_saved_wifi_networks(self):
        wifi_vault.save_wifi_network("Temp_Net", "Pass1", db_path=self.db_path)
        wifi_vault.save_wifi_network("Keep_Net", "Pass2", db_path=self.db_path)

        deleted = wifi_vault.delete_saved_wifi_network("Temp_Net", db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertIsNone(
            wifi_vault.get_wifi_password("Temp_Net", db_path=self.db_path)
        )
        self.assertFalse(
            wifi_vault.delete_saved_wifi_network("NonExistent", db_path=self.db_path)
        )

        wifi_vault.clear_saved_wifi_networks(db_path=self.db_path)
        self.assertEqual(
            len(wifi_vault.get_saved_wifi_networks(db_path=self.db_path)), 0
        )


if __name__ == "__main__":
    unittest.main()
