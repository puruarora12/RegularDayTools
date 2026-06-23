from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdftools.compress import write_pdf
from pdftools.images_to_pdf import (
    _load_rgb_image,
    _render_image_page,
    is_image,
    is_pdf,
)
from pdftools.pdf_io import open_pdf_reader
from pdftools.options import OutputOptions


@dataclass
class PreviewPage:
    source_path: Path
    source_page_index: int = 0
    rotation: int = 0

    def rotate_left(self) -> None:
        self.rotation = (self.rotation - 90) % 360

    def rotate_right(self) -> None:
        self.rotation = (self.rotation + 90) % 360

    def list_label(self, index: int) -> str:
        rotation_hint = f"  ↻{self.rotation}°" if self.rotation else ""
        if is_pdf(self.source_path):
            return f"{index + 1}. {self.source_path.name} (p.{self.source_page_index + 1}){rotation_hint}"
        return f"{index + 1}. {self.source_path.name}{rotation_hint}"


def build_preview_pages(input_paths: list[Path]) -> list[PreviewPage]:
    if not input_paths:
        raise ValueError("No input files provided.")

    pages: list[PreviewPage] = []

    for path in input_paths:
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        if is_image(path):
            pages.append(PreviewPage(source_path=path))
            continue

        if not is_pdf(path):
            raise ValueError(f"Unsupported file type: {path.name}")

        reader = open_pdf_reader(path)

        for page_index in range(len(reader.pages)):
            pages.append(PreviewPage(source_path=path, source_page_index=page_index))

    return pages


def _apply_rotation(image: Image.Image, rotation: int) -> Image.Image:
    if not rotation:
        return image
    return image.rotate(-rotation, expand=True)


def _fit_dimensions(image_size: tuple[int, int], box_size: tuple[int, int]) -> tuple[int, int]:
    img_w, img_h = image_size
    box_w, box_h = box_size
    if img_w <= 0 or img_h <= 0 or box_w <= 0 or box_h <= 0:
        return max(box_w, 1), max(box_h, 1)
    scale = min(box_w / img_w, box_h / img_h)
    return max(1, int(img_w * scale)), max(1, int(img_h * scale))


def _pdf_page_size(path: Path, page_index: int, rotation: int) -> tuple[float, float]:
    with fitz.open(path) as document:
        rect = document.load_page(page_index).rect
        width, height = rect.width, rect.height

    if rotation in (90, 270):
        return height, width
    return width, height


def _render_pdf_page_image(path: Path, page_index: int, zoom: float) -> Image.Image:
    with fitz.open(path) as document:
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def render_preview_image(page: PreviewPage, fit_size: tuple[int, int]) -> Image.Image:
    """Render a page scaled to fit inside fit_size (width, height), preserving aspect ratio."""
    box_w = max(int(fit_size[0]), 1)
    box_h = max(int(fit_size[1]), 1)

    if is_image(page.source_path):
        image = _load_rgb_image(page.source_path)
        try:
            image = _apply_rotation(image, page.rotation)
            target = _fit_dimensions(image.size, (box_w, box_h))
            if target != image.size:
                fitted = image.resize(target, Image.Resampling.LANCZOS)
                return fitted.copy()
            return image.copy()
        finally:
            image.close()

    page_w, page_h = _pdf_page_size(page.source_path, page.source_page_index, page.rotation)
    render_scale = min(box_w / page_w, box_h / page_h) * 1.5
    render_scale = max(render_scale, 0.1)

    image = _render_pdf_page_image(page.source_path, page.source_page_index, render_scale)
    image = _apply_rotation(image, page.rotation)

    target = _fit_dimensions(image.size, (box_w, box_h))
    if target != image.size:
        fitted = image.resize(target, Image.Resampling.LANCZOS)
        image.close()
        return fitted

    return image


def combine_preview_pages(
    pages: list[PreviewPage],
    output_path: Path,
    options: OutputOptions | None = None,
) -> int:
    if not pages:
        raise ValueError("No pages to save.")

    opts = options or OutputOptions()
    writer = PdfWriter()

    for page in pages:
        if is_image(page.source_path):
            image = _load_rgb_image(page.source_path)
            try:
                image = _apply_rotation(image, page.rotation)
                pdf_bytes = _render_image_page(image, opts)
            finally:
                image.close()

            reader = PdfReader(io.BytesIO(pdf_bytes))
            writer.add_page(reader.pages[0])
            continue

        reader = open_pdf_reader(page.source_path)

        pdf_page = reader.pages[page.source_page_index]
        if page.rotation:
            pdf_page.rotate(page.rotation)
        writer.add_page(pdf_page)

    write_pdf(writer, output_path, opts)
    return len(pages)
