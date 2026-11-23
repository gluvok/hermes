"""keygen.py — CLI tool to generate and sign bespoke client licenses with Ed25519.

The private signing key never lives in the repo: pass --key-file or set HERMES_LICENSE_SIGNING_KEY.
Create one with --new-keypair PATH, then put the printed public key in src/config/license.py.
"""
from __future__ import annotations

import argparse
import os
import sys

SIGNING_KEY_ENV = "HERMES_LICENSE_SIGNING_KEY"


def load_signing_key(key_file: str | None = None) -> str:
    """Private key hex from key_file or the env; exits instead of falling back to anything."""
    if key_file:
        with open(key_file, encoding="utf-8") as f:
            return f.read().strip()
    if key := os.environ.get(SIGNING_KEY_ENV, "").strip():
        return key
    sys.exit(f"[Keygen] No signing key: pass --key-file or set {SIGNING_KEY_ENV}.")


def new_keypair(key_file: str) -> str:
    """Writes a fresh private key (hex, mode 0600) to key_file; returns the public key hex."""
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    if os.path.exists(key_file):
        sys.exit(f"[Keygen] {key_file} already exists; refusing to overwrite a signing key.")
    priv = ed25519.Ed25519PrivateKey.generate()
    fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(priv.private_bytes_raw().hex() + "\n")
    return priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def generate_client_license(
    device_id: str,
    device_key: str,
    center_id: int,
    min_weight: float = 70.0,
    key_file: str | None = None,
    output_path: str = "data/client.lic",
) -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    from src.config.license import sign_license

    payload = {
        "device_id": device_id,
        "device_key": device_key,
        "center_id": center_id,
        "min_weight": min_weight,
    }
    content = sign_license(payload, load_signing_key(key_file))
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[Keygen] Signed license for '{device_id}' -> {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes Client License Generator")
    parser.add_argument("--new-keypair", metavar="PATH", help="Create a signing key at PATH (0600) and print its public key")
    parser.add_argument("--device-id", help="Client device ID (e.g. pi1)")
    parser.add_argument("--device-key", help="Client pre-shared key")
    parser.add_argument("--center-id", type=int, help="Collection center ID")
    parser.add_argument("--min-weight", type=float, default=70.0, help="Min weight threshold")
    parser.add_argument("--key-file", help=f"Private signing key file (else ${SIGNING_KEY_ENV})")
    parser.add_argument("--output", default="data/client.lic", help="Output path")
    args = parser.parse_args()

    if args.new_keypair:
        pub = new_keypair(args.new_keypair)
        print(f"[Keygen] Private key written to {args.new_keypair} (keep it out of the repo).")
        print(f"[Keygen] Set DEFAULT_PUB_KEY in src/config/license.py to:\n{pub}")
        return
    if not (args.device_id and args.device_key and args.center_id is not None):
        parser.error("--device-id, --device-key and --center-id are required to sign a license")
    generate_client_license(
        args.device_id, args.device_key, args.center_id,
        args.min_weight, args.key_file, args.output,
    )


if __name__ == "__main__":
    main()
