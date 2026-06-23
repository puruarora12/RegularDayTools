#!/usr/bin/env python3
"""Create sample images for testing image-to-PDF conversion."""

from pathlib import Path

from PIL import Image, ImageDraw


def create_samples(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    specs = [
        ("sample_red.png", (220, 120), "#e74c3c", "Page 1"),
        ("sample_blue.png", (220, 120), "#3498db", "Page 2"),
        ("sample_green.jpg", (220, 120), "#2ecc71", "Page 3"),
    ]

    for filename, size, color, label in specs:
        image = Image.new("RGB", size, color)
        draw = ImageDraw.Draw(image)
        draw.text((16, 48), label, fill="white")
        path = output_dir / filename
        image.save(path)
        created.append(path)

    return created


if __name__ == "__main__":
    samples = create_samples(Path(__file__).resolve().parent / "samples")
    for path in samples:
        print(path)
