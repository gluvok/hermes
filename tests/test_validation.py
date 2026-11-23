import pytest

from src.config.client_config import SERIAL_PORT
from src.config.constants import DEFAULT_SERIAL_PORT
from src.web.validation import is_valid_url, validate_config_payload


@pytest.mark.parametrize("char", ['"', "'", "<", ">"])
def test_is_valid_url_rejects_html_metacharacters(char):
    assert not is_valid_url(f"http://x/{char}onmouseover=1")


def test_is_valid_url_accepts_plain_urls():
    assert is_valid_url("rtsp://admin:pw@192.168.1.10:554/stream")
    assert is_valid_url("")


@pytest.mark.parametrize(
    "port",
    [
        "/dev/ttyAMA0",
        "/dev/ttyAMA10",
        "/dev/serial0",
        "/dev/serial1",
        "/dev/ttyUSB0",
        "/dev/ttyACM1",
        "/dev/ttyS0",
        "/dev/serial/by-id/usb-FTDI_FT232R-if00-port0",
        SERIAL_PORT,
        DEFAULT_SERIAL_PORT,
    ],
)
def test_accepts_serial_devices(port):
    assert validate_config_payload({"serial_port": port})[0] is True


@pytest.mark.parametrize(
    "port",
    [
        "/dev/watchdog",
        "/etc/passwd",
        "/dev/ttyAMA0/../../etc/passwd",
        "/dev/sda",
        "ttyAMA0",
        "/dev/serial/by-id/../../mem",
        "/dev/serial/by-id/..",
        "/dev/serial/by-id/.",
        "/dev/serial/by-id/",
        "/dev/serial/by-id/usb-x/../../mem",
        "/dev/serial2",
        "/dev/ttyAMA100",
        "/dev/ttyAMA",
    ],
)
def test_rejects_non_serial_paths(port):
    assert validate_config_payload({"serial_port": port})[0] is False
