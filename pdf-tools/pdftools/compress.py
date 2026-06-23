from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdftools.pdf_io import open_pdf_reader
from pdftools.options import OutputOptions


def apply_pdf_compression(writer: PdfWriter, options: OutputOptions) -> None:
    if not options.compress:
        return

    for page in writer.pages:
        page.compress_content_streams(level=9)

    if hasattr(writer, "compress_identical_objects"):
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)


def write_pdf(writer: PdfWriter, output_path: Path, options: OutputOptions) -> None:
    apply_pdf_compression(writer, options)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as out_file:
        writer.write(out_file)


def compress_pdf(input_path: Path, output_path: Path, options: OutputOptions) -> int:
    """Re-save a PDF with stream compression. Returns page count."""
    if not input_path.is_file():
        raise FileNotFoundError(f"File not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {input_path.name}")

    reader = open_pdf_reader(input_path)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    write_pdf(writer, output_path, options)
    return len(writer.pages)


def format_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"
