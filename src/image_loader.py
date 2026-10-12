"""In-memory vehicle image loading in natural order."""
import re
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass(frozen=True)
class InMemoryImage:
    name: str
    data: bytes
    index: int


def extract_image_index(path: Path) -> int:
    match = re.search(r"\d+", path.stem)
    return int(match.group()) if match else 0


def load_images_to_memory(directory: Path) -> list[InMemoryImage]:
    valid_exts = {".jpg", ".jpeg", ".png"}
    if not directory.exists():
        logger.warning(f"Directory {directory} does not exist.")
        return []

    paths = sorted(
        [p for p in directory.iterdir() if p.suffix.lower() in valid_exts],
        key=extract_image_index,
    )
    images = [
        InMemoryImage(
            name=p.name,
            data=p.read_bytes(),
            index=extract_image_index(p),
        )
        for p in paths
    ]
    total_mb = sum(len(img.data) for img in images) / (1024 * 1024)
    logger.info(f"Loaded {len(images)} images into RAM ({total_mb:.2f} MB)")
    return images
