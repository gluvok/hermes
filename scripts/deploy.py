"""deploy.py — Remote Raspberry Pi deployment automation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXCLUDES = [
    "--exclude=.venv",
    "--exclude=dist",
    "--exclude=__pycache__",
    "--exclude=.git",
    "--exclude=tests",
    "--exclude=docs",
    "--exclude=*.db",
]


def run_cmd(cmd: list[str]) -> None:
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"[Deploy] Command failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(result.returncode)


def deploy_remote(
    host: str, target: str = "/opt/hermes", lic: str = "data/client.lic"
) -> None:
    print(f"[Deploy] 1. Preparing {target} on {host}...")
    prep = (
        f"sudo mkdir -p {target} && sudo chown -R $USER:$USER {target}; "
        f"command -v ccache >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq ccache) || true; "
        f'export PATH="$HOME/.local/bin:$PATH"; command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh'
    )
    run_cmd(["ssh", "-t", host, prep])

    print(f"[Deploy] 2. Syncing source to {host}:{target}...")
    run_cmd(["rsync", "-avz", "--delete", *EXCLUDES, "./", f"{host}:{target}/"])

    print(f"[Deploy] 3. Building runtime environment into {target}...")
    build = (
        f'set -e; export PATH="$HOME/.local/bin:$PATH"; cd {target} && uv sync && '
        f"uv run python scripts/build.py --output-dir={target}/bin && chmod +x {target}/run.sh {target}/bin/hermes; "
        f"rm -f {target}/bin/hermes.sh; "
        f"echo '[Deploy] Deployment build successful at {target}.'"
    )
    run_cmd(["ssh", "-t", host, build])

    print("[Deploy] 4. Provisioning systemd service & client license...")
    svc = (
        "[Unit]\n"
        "Description=Hermes Weighbridge Edge Service\n"
        "After=network-online.target\n"
        "[Service]\n"
        "Type=simple\n"
        "User=root\n"
        f"WorkingDirectory={target}\n"
        f"ExecStart={target}/run.sh\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )
    os.makedirs("dist", exist_ok=True)
    with open("dist/hermes.service", "w", encoding="utf-8") as f:
        f.write(svc)

    run_cmd(["scp", "dist/hermes.service", f"{host}:/tmp/hermes.service"])
    run_cmd(
        [
            "ssh",
            "-t",
            host,
            (
                f"sudo mv /tmp/hermes.service /etc/systemd/system/hermes.service && "
                f"sudo systemctl daemon-reload && sudo systemctl enable --now hermes && mkdir -p {target}/data"
            ),
        ]
    )

    if os.path.exists(lic):
        run_cmd(["scp", lic, f"{host}:{target}/data/client.lic"])
        run_cmd(["ssh", "-t", host, "sudo systemctl restart hermes"])

    print(
        f"\n[Deploy] Complete! Hermes active & running 24/7 on {host} via {target}/run.sh."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes Pi Deployer")
    parser.add_argument("--host", required=True)
    parser.add_argument("--target", default="/opt/hermes")
    parser.add_argument("--license", default="data/client.lic")
    parser.add_argument("--device-id")
    parser.add_argument("--device-key")
    parser.add_argument("--center-id", type=int)
    parser.add_argument("--min-weight", type=float, default=70.0)
    args = parser.parse_args()

    if args.device_id and args.device_key and args.center_id:
        from scripts.keygen import generate_client_license

        generate_client_license(
            args.device_id,
            args.device_key,
            args.center_id,
            args.min_weight,
            output_path=args.license,
        )

    deploy_remote(args.host, args.target, args.license)


if __name__ == "__main__":
    main()
