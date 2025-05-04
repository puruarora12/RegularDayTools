# Image to PDF Converter

A Python application for combining multiple images into a single PDF file with advanced editing capabilities. This project provides two implementation options: a PySide6 (Qt) version and a Tkinter version for maximum compatibility.

## Features

- **Add multiple images** from your file system
- **Edit images** before converting:
  - Rotate images (90° clockwise or counterclockwise)
  - Crop images (basic implementation included)
  - Change orientation (landscape/portrait/auto)
  - Reorder images using up/down controls
  - Delete unwanted images
- **Generate PDF** with all images as separate pages
- **Modern UI** built with PyQt6

## Requirements

- Python 3.8 or higher
- Dependencies listed in `requirements.txt` (for PySide6 version) or `tkinter_requirements.txt` (for Tkinter version)

### PySide6 Version
- PySide6 (Qt library)
- Pillow (Python Imaging Library)
- img2pdf

### Tkinter Version (Alternative)
- Tkinter (included in standard Python installation)
- Pillow (Python Imaging Library)
- img2pdf

## Installation

1. Clone this repository or download the source code:
   ```
   git clone https://github.com/yourusername/image-to-pdf-converter.git
   cd image-to-pdf-converter
   ```

2. Create and activate a virtual environment (recommended):
   ```
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install required dependencies:

   **For PySide6 (Qt) version:**
   ```
   pip install -r requirements.txt
   ```
   
   **For Tkinter version:**
   ```
   pip install -r tkinter_requirements.txt
   ```

## Usage

1. Run the application:

   **For PySide6 (Qt) version:**
   ```
   python main.py
   ```

   **For Tkinter version:**
   ```
   python tkinter_app.py
   ```

2. Click the "Add Images" button to select images from your file system.

3. For each image, you can:
   - Rotate by clicking the rotation buttons
   - Change orientation using the dropdown menu
   - Crop the image (currently simplified)
   - Reorder using the up/down arrows
   - Delete unwanted images

4. Click "Generate PDF" to create and save your PDF file.

## Implementation Notes

- Both versions include a visual cropping interface that allows you to select the crop area using your mouse.
- Temporary files are created during PDF generation and automatically cleaned up afterward.
- The application handles image format conversion to ensure compatibility with the PDF format.

### Version Differences

#### PySide6 Version
- More modern UI with better styling capabilities
- Potentially better scaling on high-DPI displays
- Requires additional libraries

#### Tkinter Version
- Uses Python's built-in UI toolkit
- More compatible across different systems
- Simpler installation (no additional UI libraries needed)
- Slightly simpler implementation

## Future Enhancements

- Advanced cropping interface with visual selection
- Image filters and adjustments (brightness, contrast, etc.)
- Preview of the final PDF before generation
- Support for text annotations
- Ability to save and load projects

## License

This project is licensed under the MIT License - see the LICENSE file for details.