from __future__ import annotations

import tempfile

from src.config.manager import ConfigManager


def test_crop_padding_defaults():
    with tempfile.NamedTemporaryFile() as tmp:
        cfg = ConfigManager(db_path=tmp.name)
        assert cfg.crop_pad_top == 10.0
        assert cfg.crop_pad_bottom == 10.0
        assert cfg.crop_pad_left == 15.0
        assert cfg.crop_pad_right == 15.0


def test_crop_padding_persistence():
    with tempfile.NamedTemporaryFile() as tmp:
        cfg = ConfigManager(db_path=tmp.name)
        cfg.update_system_config(
            crop_pad_top=12.5,
            crop_pad_bottom=18.0,
            crop_pad_left=22.0,
            crop_pad_right=25.0,
        )

        # Re-instantiate from the same SQLite file to simulate restart
        cfg_reloaded = ConfigManager(db_path=tmp.name)
        assert cfg_reloaded.crop_pad_top == 12.5
        assert cfg_reloaded.crop_pad_bottom == 18.0
        assert cfg_reloaded.crop_pad_left == 22.0
        assert cfg_reloaded.crop_pad_right == 25.0
