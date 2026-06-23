#!/usr/bin/env python3
"""Legacy entry point — forwards to pdf-tools."""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "pdf-tools"
sys.path.insert(0, str(TOOLS_DIR))

from pdf_tools import main as tools_main  # noqa: E402


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("--gui", "-h", "--help"):
        return tools_main([] if not argv else argv)

    output_index = next((i for i, arg in enumerate(argv) if arg in ("-o", "--output")), None)
    if output_index is None:
        print("Error: --output / -o is required.", file=sys.stderr)
        return 1

    output_path = argv[output_index + 1]
    inputs = [
        arg
        for i, arg in enumerate(argv)
        if i not in (output_index, output_index + 1) and not arg.startswith("-")
    ]

    return tools_main(["merge", *inputs, "-o", output_path])


if __name__ == "__main__":
    raise SystemExit(main())
