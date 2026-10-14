"""Unit tests for RAM image loading and natural ordering."""
from pathlib import Path

from src.image_loader import extract_image_index, load_images_to_memory


def test_extract_image_index() -> None:
    assert extract_image_index(Path("10.jpg")) == 10
    assert extract_image_index(Path("car_5.png")) == 5
    assert extract_image_index(Path("no_number.jpg")) == 0


def test_natural_sorting_and_ram_load(tmp_path: Path) -> None:
    for name in ["10.jpg", "1.jpg", "2.jpg"]:
        (tmp_path / name).write_bytes(b"image_content")
    images = load_images_to_memory(tmp_path)
    assert [img.name for img in images] == ["1.jpg", "2.jpg", "10.jpg"]
    assert images[0].data == b"image_content"


def test_load_images_nonexistent_dir(tmp_path: Path) -> None:
    images = load_images_to_memory(tmp_path / "missing")
    assert images == []
