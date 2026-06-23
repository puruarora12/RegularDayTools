from __future__ import annotations

from pathlib import Path

from pdftools.options import OutputOptions
from pdftools.preview import build_preview_pages, combine_preview_pages


def merge_pdfs(
    input_paths: list[Path],
    output_path: Path,
    options: OutputOptions | None = None,
) -> int:
    """Combine PDFs and/or images in order. Images become one page each."""
    return combine_files(input_paths, output_path, options)


def combine_files(
    input_paths: list[Path],
    output_path: Path,
    options: OutputOptions | None = None,
) -> int:
    """Combine PDFs and/or images in order. Returns total page count."""
    pages = build_preview_pages(input_paths)
    return combine_preview_pages(pages, output_path, options)
