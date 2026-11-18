"""Scan source files for hardcoded passwords, default keys, and plaintext storage."""
import re
from pathlib import Path

PATTERNS = [
    (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password variable"),
    (r'DEVICE_KEY\s*=\s*["\'][^"\']+["\']', "Hardcoded device key"),
    (r'rtsp://[^:]+:[^@]+@', "RTSP URL with embedded credentials"),
    (r'SUPERADMIN_PASS\s*=\s*os\.getenv\([^,]+,\s*["\'][^"\']+["\']\)', "Default superadmin password fallback"),
]

def scan_file(path: Path) -> list[tuple[int, str, str]]:
    findings = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines, 1):
        for pattern, label in PATTERNS:
            if re.search(pattern, line):
                findings.append((idx, label, line.strip()))
    return findings

def main():
    root = Path("src")
    total = 0
    for p in root.rglob("*.py"):
        hits = scan_file(p)
        if hits:
            print(f"File: {p}")
            for lno, label, line in hits:
                print(f"  Line {lno} [{label}]: {line}")
                total += 1
    print(f"\nTotal credential vulnerabilities flagged: {total}")

if __name__ == "__main__":
    main()
