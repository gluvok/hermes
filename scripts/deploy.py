"""deploy.py — 1-command remote Pi deploy: keygen, compile, systemd, purge source."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDES = ["--exclude=.venv", "--exclude=dist", "--exclude=__pycache__", "--exclude=.git", "--exclude=tests", "--exclude=docs", "--exclude=*.db"]


REQUIRED_SECRETS = ("SUPERADMIN_PASS", "HERMES_HOTSPOT_PASS")


def run_cmd(cmd: list[str], input: str | None = None) -> None:
    if (code := subprocess.run(cmd, check=False, input=input, text=True).returncode) != 0:
        print(f"[Deploy] Command failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(code)


def secrets_env_text() -> str:
    """KEY="value" lines for systemd's EnvironmentFile; exits 1 if a required secret is unset (#33)."""
    missing = [n for n in REQUIRED_SECRETS if not os.environ.get(n)]
    if missing:
        print(f"[Deploy] Set {', '.join(missing)} in your local environment first.", file=sys.stderr)
        sys.exit(1)
    esc = lambda v: v.replace("\\", "\\\\").replace('"', '\\"')
    return "".join(f'{n}="{esc(os.environ[n])}"\n' for n in REQUIRED_SECRETS)


def deploy_remote(host: str, target: str = "/opt/hermes", lic: str = "data/client.lic") -> None:
    env_text = secrets_env_text()
    print(f"[Deploy] 1. Preparing {target} on {host}...")
    prep = (
        f"sudo mkdir -p {target} && sudo chown -R $USER:$USER {target}; "
        f"command -v ccache >/dev/null || (sudo apt-get update -qq && sudo apt-get install -y -qq ccache) || true; "
        f"export PATH=\"$HOME/.local/bin:$PATH\"; command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh"
    )
    run_cmd(["ssh", "-t", host, prep])
    print(f"[Deploy] 2. Syncing source to {host}:{target}...")
    run_cmd(["rsync", "-avz", "--delete", *EXCLUDES, "./", f"{host}:{target}/"])
    print(f"[Deploy] 3. Compiling binary into {target}/bin/ and purging source...")
    build = (
        f"set -e; export PATH=\"$HOME/.local/bin:$PATH\"; cd {target} && uv sync && uv run python scripts/build.py --output-dir={target}/bin && chmod +x {target}/run.sh {target}/bin/hermes; "
        f"rm -f {target}/bin/hermes.sh; find {target} -maxdepth 1 -name '*.py' -delete && find {target}/src -name '*.py' -delete; rm -rf {target}/scripts {target}/tests {target}/docs; "
        f"echo '[Deploy] Source purged! Only bin/hermes and run.sh remain at {target}.'"
    )
    run_cmd(["ssh", "-t", host, build])
    print("[Deploy] 4. Provisioning systemd service & client license...")
    svc = f"[Unit]\nDescription=Hermes\nAfter=network-online.target\n[Service]\nType=simple\nUser=root\nWorkingDirectory={target}\nExecStart={target}/run.sh\nRestart=always\nRestartSec=5\nEnvironment=PYTHONUNBUFFERED=1\nEnvironmentFile={target}/data/hermes.env\n[Install]\nWantedBy=multi-user.target\n"
    os.makedirs("dist", exist_ok=True)
    with open("dist/hermes.service", "w", encoding="utf-8") as f: f.write(svc)
    run_cmd(["ssh", host, f"umask 077 && mkdir -p {target}/data && cat > {target}/data/hermes.env"], input=env_text)
    run_cmd(["scp", "dist/hermes.service", f"{host}:/tmp/hermes.service"])
    run_cmd(["ssh", "-t", host, f"sudo mv /tmp/hermes.service /etc/systemd/system/hermes.service && sudo systemctl daemon-reload && sudo systemctl enable --now hermes && mkdir -p {target}/data"])
    if os.path.exists(lic):
        run_cmd(["scp", lic, f"{host}:{target}/data/client.lic"])
        run_cmd(["ssh", "-t", host, "sudo systemctl restart hermes"])
    print(f"\n[Deploy] Complete! Hermes active & running 24/7 on {host} via {target}/run.sh.")


def main() -> None:
    p = argparse.ArgumentParser(description="Hermes 1-Command Pi Deployer")
    p.add_argument("--host", required=True); p.add_argument("--target", default="/opt/hermes"); p.add_argument("--license", default="data/client.lic")
    p.add_argument("--device-id"); p.add_argument("--device-key"); p.add_argument("--center-id", type=int); p.add_argument("--min-weight", type=float, default=70.0)
    a = p.parse_args()
    if a.device_id and a.device_key and a.center_id:
        from scripts.keygen import generate_client_license
        generate_client_license(a.device_id, a.device_key, a.center_id, a.min_weight, output_path=a.license)
    deploy_remote(a.host, a.target, a.license)


if __name__ == "__main__":
    main()
