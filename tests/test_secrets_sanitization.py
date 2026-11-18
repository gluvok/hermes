import inspect

from src.config import client_config


def test_no_hardcoded_passwords_in_git():
    source = inspect.getsource(client_config)
    assert "Poly@123" not in source
    assert "Poly%40123" not in source
    assert "Cctv@222" not in source
    assert "Cctv%40222" not in source
    assert "SecretPassword123" not in source


def test_client_config_defaults_fall_back_to_env():
    assert isinstance(client_config.DEVICE_ID, (str, int))
    assert isinstance(client_config.WIFI_PASSWORD, str)
    assert isinstance(client_config.ANPR_CAMERA_URLS, list)
