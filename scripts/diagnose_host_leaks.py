"""Audit codebase for direct OS/hardware invocations bypassing simulation abstractions."""
import ast
import os
import sys

SUSPICIOUS_CALLS = {"subprocess", "serial", "periphery", "system"}

def audit_file(filepath: str) -> list[str]:
    findings = []
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(s in alias.name for s in SUSPICIOUS_CALLS):
                    findings.append(f"Line {node.lineno}: Direct import of '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            if node.module and any(s in node.module for s in SUSPICIOUS_CALLS):
                findings.append(f"Line {node.lineno}: Direct from-import of '{node.module}'")
    return findings

def main():
    root_dir = "src"
    total = 0
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                p = os.path.join(root, file)
                issues = audit_file(p)
                if issues:
                    print(f"[{p}]")
                    for iss in issues:
                        print(f"  {iss}")
                    total += len(issues)
    print(f"\nTotal hardware/OS direct boundaries found: {total}")
    sys.exit(0)

if __name__ == "__main__":
    main()
