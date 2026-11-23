"""test_keygen.py — The license signing key must never come from the repo."""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from scripts import keygen
from src.config.license import verify_license


def test_keygen_has_no_committed_private_key() -> None:
    assert not hasattr(keygen, "DEFAULT_PRIV_KEY")


def test_load_signing_key_refuses_without_env_or_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(keygen.SIGNING_KEY_ENV, raising=False)
    with pytest.raises(SystemExit):
        keygen.load_signing_key()


def test_new_keypair_writes_private_file_0600_and_signs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_file = tmp_path / "signing.key"
    pub_hex = keygen.new_keypair(str(key_file))
    assert stat.S_IMODE(os.stat(key_file).st_mode) == 0o600

    monkeypatch.delenv(keygen.SIGNING_KEY_ENV, raising=False)
    lic = tmp_path / "client.lic"
    keygen.generate_client_license("pi9", "k", 7, key_file=str(key_file), output_path=str(lic))
    assert verify_license(lic.read_text(encoding="utf-8"), pub_hex)["device_id"] == "pi9"


def test_load_signing_key_reads_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_file = tmp_path / "signing.key"
    keygen.new_keypair(str(key_file))
    monkeypatch.setenv(keygen.SIGNING_KEY_ENV, key_file.read_text(encoding="utf-8").strip())
    assert keygen.load_signing_key() == key_file.read_text(encoding="utf-8").strip()


def test_new_keypair_refuses_to_overwrite(tmp_path: Path) -> None:
    key_file = tmp_path / "signing.key"
    keygen.new_keypair(str(key_file))
    with pytest.raises(SystemExit):
        keygen.new_keypair(str(key_file))
