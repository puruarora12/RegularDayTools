from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputOptions:
    dpi: int = 150
    jpeg_quality: int = 85
    compress: bool = True
    max_image_dimension: int | None = None

    def __post_init__(self) -> None:
        if not 72 <= self.dpi <= 600:
            raise ValueError("DPI must be between 72 and 600.")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("JPEG quality must be between 1 and 100.")
        if self.max_image_dimension is not None and self.max_image_dimension < 256:
            raise ValueError("Max image dimension must be at least 256 pixels.")


PRESETS: dict[str, OutputOptions] = {
    "high": OutputOptions(dpi=300, jpeg_quality=95, compress=False, max_image_dimension=None),
    "balanced": OutputOptions(dpi=150, jpeg_quality=85, compress=True, max_image_dimension=2400),
    "small": OutputOptions(dpi=96, jpeg_quality=65, compress=True, max_image_dimension=1600),
}


def options_from_preset(preset: str) -> OutputOptions:
    key = preset.lower()
    if key not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Choose: {', '.join(PRESETS)}")
    return PRESETS[key]


def build_options(
    *,
    preset: str | None = None,
    dpi: int | None = None,
    jpeg_quality: int | None = None,
    compress: bool | None = None,
    max_image_dimension: int | None = None,
) -> OutputOptions:
    base = options_from_preset(preset) if preset else OutputOptions()
    return OutputOptions(
        dpi=dpi if dpi is not None else base.dpi,
        jpeg_quality=jpeg_quality if jpeg_quality is not None else base.jpeg_quality,
        compress=compress if compress is not None else base.compress,
        max_image_dimension=(
            max_image_dimension if max_image_dimension is not None else base.max_image_dimension
        ),
    )
