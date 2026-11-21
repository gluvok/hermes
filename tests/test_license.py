"""test_license.py — Unit tests for Ed25519 offline license verification."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.config import license as lic_mod
from src.config.license import load_client_license, sign_license, verify_license
from src.config.manager import ConfigManager


@pytest.fixture
def keypair() -> tuple[str, str]:
    """Throwaway (private_hex, public_hex); real keys never live in the repo (#33 follow-up)."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return priv.private_bytes_raw().hex(), pub.hex()


@pytest.fixture
def sample_payload() -> dict[str, object]:
    return {
        "device_id": "test_pi_99",
        "device_key": "secret_key_123",
        "center_id": 42,
        "min_weight": 85.5,
    }


def test_license_signing_and_verification(sample_payload: dict[str, object], keypair: tuple[str, str]) -> None:
    priv, pub = keypair
    assert verify_license(sign_license(sample_payload, priv), pub) == sample_payload


def test_tampered_payload_rejected(sample_payload: dict[str, object], keypair: tuple[str, str]) -> None:
    priv, pub = keypair
    tampered_data = json.loads(sign_license(sample_payload, priv))
    tampered_data["payload"]["center_id"] = 999  # Tamper with collection center ID
    with pytest.raises(InvalidSignature):
        verify_license(json.dumps(tampered_data), pub)


def test_invalid_signature_rejected(sample_payload: dict[str, object], keypair: tuple[str, str]) -> None:
    priv, pub = keypair
    data = json.loads(sign_license(sample_payload, priv))
    data["signature"] = "00" * 64  # Bogus 64-byte signature
    with pytest.raises(InvalidSignature):
        verify_license(json.dumps(data), pub)


def test_license_from_other_key_rejected(sample_payload: dict[str, object], keypair: tuple[str, str]) -> None:
    _, pub = keypair
    other_priv = ed25519.Ed25519PrivateKey.generate().private_bytes_raw().hex()
    with pytest.raises(InvalidSignature):
        verify_license(sign_license(sample_payload, other_priv), pub)


def test_no_public_key_configured_rejects_license(
    tmp_path: Path, sample_payload: dict[str, object], keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lic_mod, "DEFAULT_PUB_KEY", "")
    lic_file = tmp_path / "client.lic"
    lic_file.write_text(sign_license(sample_payload, keypair[0]), encoding="utf-8")
    assert load_client_license(str(lic_file)) is None


def test_load_client_license_missing_file() -> None:
    assert load_client_license("/nonexistent/path/client.lic") is None


def test_config_manager_with_license(
    tmp_path: Path, sample_payload: dict[str, object], keypair: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    priv, pub = keypair
    monkeypatch.setattr(lic_mod, "DEFAULT_PUB_KEY", pub)
    lic_file = tmp_path / "client.lic"
    lic_file.write_text(sign_license(sample_payload, priv), encoding="utf-8")
    db_file = tmp_path / "test.db"

    mgr = ConfigManager(db_path=str(db_file), lic_path=str(lic_file))
    assert mgr.center_id == 42
    assert mgr.device_id == "test_pi_99"
    assert mgr.device_key == "secret_key_123"
    assert mgr.weight_threshold == 85.5
    assert mgr.anpr_server_url == "http://127.0.0.1:8000/recognize"


def test_config_manager_without_license_uses_client_config_fallbacks(tmp_path: Path) -> None:
    from src.config import client_config as cc

    db_file = tmp_path / "test_fallback.db"
    mgr = ConfigManager(db_path=str(db_file), lic_path="/nonexistent/client.lic")
    assert mgr.center_id == cc.CENTER_ID
    assert mgr.device_id == cc.DEVICE_ID
    assert mgr.device_key == cc.DEVICE_KEY
