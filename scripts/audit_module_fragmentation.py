"""Analyze line counts, imports, and semicolon-compression in src/devices/wifi."""

from pathlib import Path


def analyze_directory(dir_path: Path):
    print(f"Analyzing: {dir_path}")
    total_lines = 0
    semicolon_lines = 0
    lazy_imports = 0

    for f in sorted(dir_path.glob("*.py")):
        lines = f.read_text(encoding="utf-8").splitlines()
        loc = len(lines)
        total_lines += loc
        semis = sum(1 for l in lines if ";" in l and not l.strip().startswith("#"))
        lazies = sum(1 for l in lines if l.startswith(("    from ", "        from ")))
        semicolon_lines += semis
        lazy_imports += lazies
        print(
            f"  {f.name:25s}: {loc:3d} lines | {semis:2d} semicolon lines | {lazies:2d} in-function imports"
        )

    print(
        f"\nTotal: {len(list(dir_path.glob('*.py')))} files, {total_lines} LOC, {semicolon_lines} semicolon statements, {lazy_imports} lazy imports"
    )


if __name__ == "__main__":
    analyze_directory(Path("src/devices/wifi"))
