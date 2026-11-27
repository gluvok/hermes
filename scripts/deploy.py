"""deploy.py — 1-command remote Pi deploy: keygen, compile, systemd, purge source."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDES = ["--exclude=.venv", "--exclude=dist", "--exclude=__pycache__", "--exclude=.git", "--exclude=tests", "--exclude=docs", "--exclude=*.db"]


REQUIRED_SECRETS = ("SUPERADMIN_PASS", "HERMES_HOTSPOT_PASS")
OPTIONAL_ENV_VARS = ("GLUVOK_BASE_URL", "ANPR_SERVER_TIMEOUT")  # forwarded only when set locally
SERVICE_USER = "hermes"
SERVICE_GROUPS = ("dialout", "gpio", "netdev")  # UART, /dev/gpiochip*, NetworkManager polkit
SUDOERS_PATH = "/etc/sudoers.d/hermes"
PORTAL_FALLBACK_PORT = 8088  # CaptiveHTTPServer binds this when :80 is taken


def run_cmd(cmd: list[str], input: str | None = None) -> None:
    if (code := subprocess.run(cmd, check=False, input=input, text=True).returncode) != 0:
        print(f"[Deploy] Command failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(code)


def secrets_env_text() -> str:
    """KEY="value" lines for systemd's EnvironmentFile (secrets + set optional overrides); exits 1 if a required secret is unset (#33)."""
    missing = [n for n in REQUIRED_SECRETS if not os.environ.get(n)]
    if missing:
        print(f"[Deploy] Set {', '.join(missing)} in your local environment first.", file=sys.stderr)
        sys.exit(1)
    esc = lambda v: v.replace("\\", "\\\\").replace('"', '\\"')
    env = {n: v for n in (*REQUIRED_SECRETS, *OPTIONAL_ENV_VARS) if (v := os.environ.get(n))}
    for n, v in env.items():
        if any(c in v for c in "\r\n\0"):  # a newline would inject extra EnvironmentFile lines
            print(f"[Deploy] {n} must not contain newlines.", file=sys.stderr)
            sys.exit(1)
    try:
        float(env.get("ANPR_SERVER_TIMEOUT", "0"))
    except ValueError:
        print("[Deploy] ANPR_SERVER_TIMEOUT must be a number.", file=sys.stderr)
        sys.exit(1)
    return "".join(f'{n}="{esc(v)}"\n' for n, v in env.items())


def build_service_unit(target: str) -> str:
    """systemd unit running Hermes as an unprivileged user (#29).

    Deliberately absent: NoNewPrivileges (sudo is setuid), CapabilityBoundingSet / PrivateUsers
    (sudo needs setuid/setgid caps), PrivateDevices (/dev/gpiochip*, /dev/ttyAMA0),
    RestrictAddressFamilies (nmcli talks to D-Bus, iptables uses netlink).
    ProtectSystem=strict also makes /etc read-only for sudo'd children, hence ReadWritePaths.
    """
    from src.devices.wifi.portal_capport import NM_DNSMASQ_DIR
    from src.devices.wifi.portal_hosts import DEFAULT_HOSTS

    rw = f"{target}/data {DEFAULT_HOSTS} {NM_DNSMASQ_DIR}"
    return (
        "[Unit]\nDescription=Hermes\nAfter=network-online.target\n"
        f"[Service]\nType=simple\nUser={SERVICE_USER}\nWorkingDirectory={target}\nExecStart={target}/run.sh\n"
        "Restart=always\nRestartSec=5\nEnvironment=PYTHONUNBUFFERED=1\n"
        f"EnvironmentFile={target}/data/hermes.env\n"
        "AmbientCapabilities=CAP_NET_BIND_SERVICE\nProtectSystem=strict\n"
        f"ReadWritePaths={rw}\nPrivateTmp=yes\n"
        "[Install]\nWantedBy=multi-user.target\n"
    )


def build_sudoers(iface: str = "wlan0") -> str:
    """Exactly the argv Hermes runs via `sudo -n` (src/devices/wifi/runner, portal_redirect/hosts/capport)."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", iface):
        raise ValueError(f"Unsafe interface name: {iface!r}")
    from src.devices.wifi.constants import DEFAULT_DNS_PORT, DEFAULT_PORTAL_PORT
    from src.devices.wifi.portal_capport import NM_CAPPORT_FILE, NM_DNSMASQ_DIR
    from src.devices.wifi.portal_hosts import DEFAULT_HOSTS

    ipt, nat = "/usr/sbin/iptables -t nat", "-j REDIRECT --to-ports"
    dns = [f"PREROUTING -i {iface} -p {p} --dport 53 {nat} {DEFAULT_DNS_PORT}" for p in ("udp", "tcp")]
    cmds = ["/usr/bin/nmcli", "/usr/bin/fuser -k -9 80/tcp", f"/usr/bin/tee {DEFAULT_HOSTS}", f"/usr/bin/mkdir -p {NM_DNSMASQ_DIR}",
            f"/usr/bin/tee {NM_CAPPORT_FILE}", f"/usr/bin/rm -f {NM_CAPPORT_FILE}"]
    cmds += [f"{ipt} {op} {r}" for op in ("-A", "-D") for r in dns]
    for port in (DEFAULT_PORTAL_PORT, PORTAL_FALLBACK_PORT):  # portal_redirect: -D always, -A http only off :80
        http = [f"PREROUTING -i {iface} -p tcp --dport 80 {nat} {port}", f"OUTPUT -p tcp -o lo --dport 80 {nat} {port}",
                f"OUTPUT -p tcp -d 10.42.0.1 --dport 80 {nat} {port}"]
        cmds += [f"{ipt} -D {r}" for r in http] + ([f"{ipt} -A {r}" for r in http] if port != 80 else [])
    lines = ["# Managed by scripts/deploy.py. nmcli args vary (SSIDs, passwords), so only the binary is pinned."]
    return "\n".join(lines + [f"{SERVICE_USER} ALL=(root) NOPASSWD: {c}" for c in dict.fromkeys(cmds)]) + "\n"


def provision_script(target: str) -> str:
    """Remote root-side setup: user, ownership, validated sudoers, unit install. Safe to re-run."""
    from src.devices.wifi.portal_capport import NM_DNSMASQ_DIR

    groups = " ".join(SERVICE_GROUPS)
    return (
        "set -e; "
        f"id {SERVICE_USER} >/dev/null 2>&1 || sudo useradd --system --no-create-home --shell /usr/sbin/nologin {SERVICE_USER}; "
        f"for g in {groups}; do if getent group $g >/dev/null; then sudo usermod -aG $g {SERVICE_USER}; else echo \"[Deploy] group $g missing, skipped\"; fi; done; "
        f"sudo mkdir -p {NM_DNSMASQ_DIR}; "
        f"sudo chown -R {SERVICE_USER}:{SERVICE_USER} {target}/data; sudo chmod 600 {target}/data/hermes.env; "
        "sudo visudo -cf ~/hermes.sudoers; "  # set -e: a rejected file aborts before install
        f"sudo install -m 0440 -o root -g root ~/hermes.sudoers {SUDOERS_PATH}.new; sudo mv {SUDOERS_PATH}.new {SUDOERS_PATH}; rm -f ~/hermes.sudoers; "
        "sudo mv /tmp/hermes.service /etc/systemd/system/hermes.service; sudo systemctl daemon-reload; "
        "sudo systemctl enable hermes; sudo systemctl restart hermes"
    )


def deploy_remote(host: str, target: str = "/opt/hermes", lic: str = "data/client.lic", iface: str = "wlan0") -> None:
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
    os.makedirs("dist", exist_ok=True)
    with open("dist/hermes.service", "w", encoding="utf-8") as f: f.write(build_service_unit(target))
    with open("dist/hermes.sudoers", "w", encoding="utf-8") as f: f.write(build_sudoers(iface))
    run_cmd(["ssh", host, f"umask 077 && mkdir -p {target}/data && cat > {target}/data/hermes.env"], input=env_text)
    if os.path.exists(lic):
        run_cmd(["scp", lic, f"{host}:{target}/data/client.lic"])
    run_cmd(["scp", "dist/hermes.service", f"{host}:/tmp/hermes.service"])
    run_cmd(["scp", "dist/hermes.sudoers", f"{host}:hermes.sudoers"])  # home dir, not shared /tmp
    run_cmd(["ssh", "-t", host, provision_script(target)])
    print(f"\n[Deploy] Complete! Hermes active & running 24/7 on {host} via {target}/run.sh.")


def main() -> None:
    p = argparse.ArgumentParser(description="Hermes 1-Command Pi Deployer")
    p.add_argument("--host", required=True); p.add_argument("--target", default="/opt/hermes"); p.add_argument("--license", default="data/client.lic"); p.add_argument("--wifi-iface", default="wlan0", help="Wi-Fi device name (sudoers pins it)")
    p.add_argument("--device-id"); p.add_argument("--device-key"); p.add_argument("--center-id", type=int); p.add_argument("--min-weight", type=float, default=70.0)
    a = p.parse_args()
    if a.device_id and a.device_key and a.center_id:
        from scripts.keygen import generate_client_license
        generate_client_license(a.device_id, a.device_key, a.center_id, a.min_weight, output_path=a.license)
    deploy_remote(a.host, a.target, a.license, a.wifi_iface)


if __name__ == "__main__":
    main()
