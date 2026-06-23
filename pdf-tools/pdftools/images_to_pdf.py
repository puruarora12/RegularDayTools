from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from pdftools.options import OutputOptions

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXTENSION = ".pdf"
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {PDF_EXTENSION}


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() == PDF_EXTENSION


def _load_rgb_image(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if not is_image(path):
        raise ValueError(f"Unsupported image format: {path.name}")

    with Image.open(path) as img:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
            return background.copy()
        return img.convert("RGB")


def _scale_for_output(image: Image.Image, options: OutputOptions) -> Image.Image:
    if options.max_image_dimension is None:
        return image

    width, height = image.size
    longest = max(width, height)
    if longest <= options.max_image_dimension:
        return image

    ratio = options.max_image_dimension / longest
    new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _render_image_page(image: Image.Image, options: OutputOptions) -> bytes:
    scaled = _scale_for_output(image, options)

    jpeg_buffer = io.BytesIO()
    scaled.save(
        jpeg_buffer,
        format="JPEG",
        quality=options.jpeg_quality,
        optimize=True,
        progressive=True,
    )
    jpeg_buffer.seek(0)

    with Image.open(jpeg_buffer) as jpeg_image:
        pdf_buffer = io.BytesIO()
        jpeg_image.save(pdf_buffer, format="PDF", resolution=float(options.dpi))
        return pdf_buffer.getvalue()


def image_to_pdf_bytes(path: Path, options: OutputOptions | None = None) -> bytes:
    """Convert a single image to PDF bytes (one page)."""
    opts = options or OutputOptions()
    image = _load_rgb_image(path)
    try:
        return _render_image_page(image, opts)
    finally:
        image.close()


def images_to_pdf(
    input_paths: list[Path],
    output_path: Path,
    options: OutputOptions | None = None,
) -> int:
    """Convert one or more images into a single PDF. Returns page count."""
    from pdftools.preview import build_preview_pages, combine_preview_pages

    pages = build_preview_pages(input_paths)
    return combine_preview_pages(pages, output_path, options)
