#!/usr/bin/env python3
"""PDF Tools — combine PDFs and convert images to PDF. GUI by default."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdftools.compress import compress_pdf, format_size
from pdftools.gui import run_gui
from pdftools.images_to_pdf import images_to_pdf
from pdftools.merge import merge_pdfs
from pdftools.options import build_options


def add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--preset",
        choices=["high", "balanced", "small"],
        help="Quality preset (default: balanced).",
    )
    parser.add_argument("--dpi", type=int, help="Image DPI when embedding (72-600).")
    parser.add_argument("--quality", type=int, help="JPEG quality for images (1-100).")
    parser.add_argument(
        "--max-dimension",
        type=int,
        help="Max longest edge in pixels for images (omit for no limit).",
    )
    parser.add_argument(
        "--compress",
        action=argparse.BooleanOptionalAction,
        help="Compress PDF streams in output.",
    )


def resolve_options(args: argparse.Namespace):
    return build_options(
        preset=args.preset,
        dpi=args.dpi,
        jpeg_quality=args.quality,
        compress=args.compress,
        max_image_dimension=args.max_dimension,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PDF Tools: combine PDFs, convert images, and compress PDFs.",
    )
    subparsers = parser.add_subparsers(dest="command")

    merge_parser = subparsers.add_parser(
        "merge",
        help="Combine PDFs and/or images into one PDF.",
    )
    merge_parser.add_argument("inputs", nargs="+", type=Path, help="Input PDF and/or image paths.")
    merge_parser.add_argument("-o", "--output", type=Path, required=True, help="Output PDF path.")
    add_output_options(merge_parser)

    images_parser = subparsers.add_parser("images", help="Convert images to a single PDF.")
    images_parser.add_argument("inputs", nargs="+", type=Path, help="Input image paths.")
    images_parser.add_argument("-o", "--output", type=Path, required=True, help="Output PDF path.")
    add_output_options(images_parser)

    compress_parser = subparsers.add_parser("compress", help="Compress an existing PDF.")
    compress_parser.add_argument("input", type=Path, help="Input PDF path.")
    compress_parser.add_argument("-o", "--output", type=Path, required=True, help="Output PDF path.")
    add_output_options(compress_parser)

    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch GUI (default when no subcommand is given).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui or args.command is None:
        run_gui()
        return 0

    try:
        options = resolve_options(args)
        if args.command == "merge":
            page_count = merge_pdfs(args.inputs, args.output, options)
            size_line = f", {format_size(args.output.stat().st_size)}"
            print(f"Merged {len(args.inputs)} file(s) -> {args.output} ({page_count} pages{size_line})")
        elif args.command == "images":
            page_count = images_to_pdf(args.inputs, args.output, options)
            size_line = f", {format_size(args.output.stat().st_size)}"
            print(f"Converted {len(args.inputs)} image(s) -> {args.output} ({page_count} pages{size_line})")
        elif args.command == "compress":
            before = args.input.stat().st_size
            page_count = compress_pdf(args.input, args.output, options)
            after = args.output.stat().st_size
            saved = max(0, before - after)
            pct = (saved / before * 100) if before else 0
            print(
                f"Compressed {args.input} -> {args.output} "
                f"({page_count} pages, {format_size(before)} -> {format_size(after)}, {pct:.0f}% smaller)"
            )
        else:
            parser.print_help()
            return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
