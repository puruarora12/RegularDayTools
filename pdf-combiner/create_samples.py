#!/usr/bin/env python3
"""Create small sample PDFs for testing the combiner."""

from pathlib import Path

from pypdf import PdfWriter


def create_samples(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    specs = [
        ("sample_a.pdf", 2),
        ("sample_b.pdf", 1),
        ("sample_c.pdf", 3),
    ]

    for filename, page_count in specs:
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=612, height=792)

        path = output_dir / filename
        with path.open("wb") as handle:
            writer.write(handle)
        created.append(path)

    return created


if __name__ == "__main__":
    samples = create_samples(Path(__file__).resolve().parent / "samples")
    for path in samples:
        print(path)
