"""Script to convert dataset images to 2K (2560x1440) 2.5MB JPEGs."""
from pathlib import Path

TARGET_BYTES = 2_500_000


def pad_jpeg(path: Path, target_bytes: int = TARGET_BYTES) -> None:
    data = path.read_bytes()
    if len(data) >= target_bytes or data[:2] != b"\xff\xd8":
        return
    needed = target_bytes - len(data)
    chunks: list[bytes] = []
    while needed > 4:
        chunk_len = min(needed, 65535)
        payload = b"X" * (chunk_len - 4)
        chunks.append(b"\xff\xfe" + (chunk_len - 2).to_bytes(2, "big") + payload)
        needed -= chunk_len
    if needed > 0:
        chunks[-1] += b"\x00" * needed
    path.write_bytes(data[:2] + b"".join(chunks) + data[2:])


def main() -> None:
    data_dir = Path("data")
    for img_path in sorted(data_dir.glob("*.jpg")):
        pad_jpeg(img_path)
        print(f"Padded {img_path.name} -> {img_path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
