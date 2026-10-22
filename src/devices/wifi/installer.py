"""installer.py — Automatic installation and binary management for balena wifi-connect."""
from __future__ import annotations

import logging
import os
import platform
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from src.devices.wifi.constants import BASE_DIR

logger = logging.getLogger(__name__)

ARCH_MAP = {
    "aarch64": "linux-aarch64", "arm64": "linux-aarch64",
    "armv7l": "linux-armv7hf", "armv7": "linux-armv7hf",
    "armv8l": "linux-armv7hf", "armhf": "linux-armv7hf",
    "x86_64": "linux-amd64", "amd64": "linux-amd64",
    "i386": "linux-i386", "i686": "linux-i386",
}


def get_target_arch() -> str | None:
    """Return the release architecture tag for the current machine."""
    return ARCH_MAP.get(platform.machine().lower())


def install_wifi_connect(target_dir: Path | None = None, version: str = "v4.11.1") -> Path:
    """Download and install official balena wifi-connect binary."""
    dest_dir = target_dir or (BASE_DIR / "bin")
    dest_dir.mkdir(parents=True, exist_ok=True)
    binary_dest = dest_dir / "wifi-connect"
    if binary_dest.is_file() and os.access(binary_dest, os.X_OK):
        return binary_dest

    target = get_target_arch()
    if not target:
        raise RuntimeError(f"Unsupported architecture '{platform.machine()}'.")

    zip_name = f"wifi-connect-{version}-{target}.zip"
    url = f"https://github.com/balena-os/wifi-connect/releases/download/{version}/{zip_name}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_zip = Path(tmp_dir) / zip_name
        req = urllib.request.Request(url, headers={"User-Agent": "Hermes-WiFi-Installer"})
        with urllib.request.urlopen(req, timeout=45.0) as resp, open(tmp_zip, "wb") as out:
            shutil.copyfileobj(resp, out)
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(path=tmp_dir)
        for root, _, files in os.walk(tmp_dir):
            if "wifi-connect" in files:
                shutil.copy2(Path(root) / "wifi-connect", binary_dest)
                binary_dest.chmod(0o755)
                return binary_dest
    raise RuntimeError(f"wifi-connect binary not found in {zip_name}")
