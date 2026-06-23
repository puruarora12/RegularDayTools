from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader


def _source_label(source: str | Path | io.BytesIO) -> str:
    if isinstance(source, Path):
        return source.name
    if isinstance(source, str):
        return Path(source).name
    return "PDF"


def open_pdf_reader(source: str | Path | io.BytesIO) -> PdfReader:
    """
    Open a PDF for reading.

    Many PDFs mark is_encrypted=True with an empty user password (owner restrictions only).
    Those open after decrypt(""). Only reject PDFs that need a real password.
    """
    reader = PdfReader(source, strict=False)

    if not reader.is_encrypted:
        return reader

    # Empty password unlocks most owner-restricted / nominally "encrypted" PDFs.
    if reader.decrypt("") != 0:
        return reader

    raise ValueError(f"Password-protected PDF not supported: {_source_label(source)}")
