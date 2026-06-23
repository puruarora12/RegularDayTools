# PDF Tools

Combine PDFs, convert images to PDF, and compress PDFs. Tkinter GUI by default, with a CLI for scripting.

## Features

- **Combine PDFs** — merge multiple PDFs and/or images into one file (mixed inputs supported)
- **Images to PDF** — turn image files into a multi-page PDF
- **Compress PDF** — re-save a PDF with stream compression and optional size tuning
- **Preview before save** — review pages, rotate left/right, then export
- **Drag and drop** — drop files onto the window (Windows via `windnd`, macOS/Linux via `tkinterdnd2`)
- **Output quality presets** — High, Balanced, Small, or custom DPI / JPEG quality / max image size
- **Owner-restricted PDFs** — opens PDFs that use empty user passwords (common “encrypted” exports)

Password-protected PDFs that require a real password are not supported.

## Requirements

- Python 3.10 or higher
- Dependencies in `requirements.txt`
- Tkinter (included with most Python installs)

| Package | Purpose |
|---------|---------|
| `pypdf` | PDF read, merge, and compression |
| `Pillow` | Image loading and PDF page rendering |
| `pymupdf` | Fast PDF preview rendering |
| `windnd` | Drag-and-drop on Windows |
| `tkinterdnd2` | Drag-and-drop on macOS/Linux |

## Installation

```bash
cd pdf-tools
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Usage

### GUI (default)

```bash
python pdf_tools.py
```

Or explicitly:

```bash
python pdf_tools.py --gui
```

Use the tabs **Combine PDFs**, **Images to PDF**, or **Compress PDF**. Adjust output quality at the top, add or reorder files, then **Preview && Save...**.

### CLI

**Merge PDFs and/or images:**

```bash
python pdf_tools.py merge doc1.pdf photo.jpg scan.png -o combined.pdf
```

**Convert images only:**

```bash
python pdf_tools.py images page1.png page2.jpg -o album.pdf
```

**Compress a PDF:**

```bash
python pdf_tools.py compress large.pdf -o smaller.pdf
```

**Quality options** (optional on all commands):

```bash
python pdf_tools.py merge a.pdf b.pdf -o out.pdf --preset small
python pdf_tools.py images a.png -o out.pdf --dpi 300 --quality 90 --compress
python pdf_tools.py compress in.pdf -o out.pdf --preset high --no-compress
```

Presets: `high`, `balanced` (default), `small`.

### Legacy merge script

`combine_pdfs.py` is a thin wrapper around the merge subcommand:

```bash
python combine_pdfs.py file1.pdf file2.pdf -o merged.pdf
```

## Supported formats

**Images:** `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tif`, `.tiff`, `.webp`

**Documents:** `.pdf`

## Project layout

```
pdf-tools/
├── pdf_tools.py          # Main entry (GUI + CLI)
├── combine_pdfs.py       # Legacy merge wrapper
├── requirements.txt
├── pdftools/             # Core modules
│   ├── gui.py            # Tkinter application
│   ├── merge.py
│   ├── images_to_pdf.py
│   ├── compress.py
│   ├── preview.py        # Preview + page rotation
│   └── ...
└── samples/              # Example inputs/outputs
```

## Sample files

Generate sample PDFs for testing:

```bash
python create_samples.py
python create_test_images.py
```
