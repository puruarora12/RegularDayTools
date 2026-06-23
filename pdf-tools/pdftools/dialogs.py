from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog


def default_save_dir(last_dir: Path | None, input_paths: list[Path] | None = None) -> Path:
    if last_dir is not None and last_dir.is_dir():
        return last_dir

    documents = Path.home() / "Documents"
    if documents.is_dir():
        return documents

    if input_paths:
        for path in input_paths:
            parent = path.parent
            if parent.is_dir():
                return parent

    home = Path.home()
    return home if home.is_dir() else Path.cwd()


def prompt_save_pdf_path(
    *,
    title: str,
    initialfile: str,
    last_dir: Path | None = None,
    input_paths: list[Path] | None = None,
) -> tuple[Path | None, Path | None]:
    """
    Ask where to save a PDF.

    Returns (output_path, output_dir_for_next_time).
    """
    initialdir = default_save_dir(last_dir, input_paths)

    selected = filedialog.asksaveasfilename(
        title=title,
        defaultextension=".pdf",
        initialdir=str(initialdir),
        initialfile=initialfile,
        filetypes=[("PDF files", "*.pdf")],
    )
    if not selected:
        return None, last_dir

    path = Path(os.path.normpath(selected))
    if not path.is_absolute():
        path = (initialdir / path).resolve()
    else:
        path = path.resolve()

    if path.suffix.lower() != ".pdf":
        path = path.with_suffix(".pdf")

    return path, path.parent
