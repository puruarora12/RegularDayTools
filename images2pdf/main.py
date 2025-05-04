import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QFileDialog, QScrollArea, QMessageBox,
                            QSlider, QComboBox, QSplitter)
from PyQt6.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt6.QtGui import QPixmap, QTransform, QImage, QPainter
from PIL import Image
import img2pdf
from functools import partial
from crop_dialog import CropDialog

class ImageItem(QWidget):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.rotation = 0
        self.orientation = "auto"  # "landscape", "portrait", or "auto"
        self.crop_rect = None
        self.original_pixmap = QPixmap(image_path)
        
        self.main_layout = QVBoxLayout(self)
        
        # Image preview
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_preview()
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Rotation
        rotate_left_btn = QPushButton("↺")
        rotate_left_btn.clicked.connect(lambda: self.rotate(-90))
        rotate_right_btn = QPushButton("↻")
        rotate_right_btn.clicked.connect(lambda: self.rotate(90))
        
        # Orientation
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Auto", "Portrait", "Landscape"])
        self.orientation_combo.currentTextChanged.connect(self.set_orientation)
        
        # Crop button
        crop_btn = QPushButton("Crop")
        crop_btn.clicked.connect(self.crop_image)
        
        # Reset crop button
        reset_crop_btn = QPushButton("Reset Crop")
        reset_crop_btn.clicked.connect(self.reset_crop)
        
        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_item)
        
        # Move buttons
        move_up_btn = QPushButton("↑")
        move_up_btn.clicked.connect(lambda: self.move_item("up"))
        move_down_btn = QPushButton("↓")
        move_down_btn.clicked.connect(lambda: self.move_item("down"))
        
        # Add controls to layout
        controls_layout.addWidget(rotate_left_btn)
        controls_layout.addWidget(rotate_right_btn)
        controls_layout.addWidget(self.orientation_combo)
        controls_layout.addWidget(crop_btn)
        controls_layout.addWidget(reset_crop_btn)
        controls_layout.addWidget(delete_btn)
        controls_layout.addWidget(move_up_btn)
        controls_layout.addWidget(move_down_btn)
        
        # Add to main layout
        self.main_layout.addWidget(self.image_label)
        self.main_layout.addLayout(controls_layout)
        
        # Set fixed height
        self.setFixedHeight(280)

    def update_preview(self):
        pixmap = self.original_pixmap.copy()
        
        # Apply crop if exists
        if self.crop_rect:
            pixmap = pixmap.copy(self.crop_rect)
        
        # Apply rotation
        if self.rotation != 0:
            transform = QTransform().rotate(self.rotation)
            pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        
        # Scale for preview
        pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, 
                               Qt.TransformationMode.SmoothTransformation)
        
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(QSize(200, 200))
    
    def rotate(self, degrees):
        self.rotation = (self.rotation + degrees) % 360
        self.update_preview()
    
    def set_orientation(self, orientation):
        self.orientation = orientation.lower()
        self.update_preview()
    
    def crop_image(self):
        # Open the crop dialog with the original image
        crop_dialog = CropDialog(self.original_pixmap, self)
        if crop_dialog.exec():
            # Get the crop rectangle
            self.crop_rect = crop_dialog.get_crop_rect_for_original()
            self.update_preview()
    
    def reset_crop(self):
        self.crop_rect = None
        self.update_preview()
    
    def delete_item(self):
        parent_layout = self.parent().layout()
        parent_layout.removeWidget(self)
        self.deleteLater()
    
    def move_item(self, direction):
        parent_layout = self.parent().layout()
        current_index = parent_layout.indexOf(self)
        
        if direction == "up" and current_index > 0:
            widget = parent_layout.takeAt(current_index).widget()
            parent_layout.insertWidget(current_index - 1, widget)
        elif direction == "down" and current_index < parent_layout.count() - 1:
            widget = parent_layout.takeAt(current_index).widget()
            parent_layout.insertWidget(current_index + 1, widget)
    
    def get_processed_image(self):
        """Return a PIL Image with all modifications applied"""
        # Convert QPixmap to PIL Image
        qimage = self.original_pixmap.toImage()
        width, height = qimage.width(), qimage.height()
        
        # Create PIL Image from QImage
        byte_count = qimage.sizeInBytes()
        buffer = qimage.bits().asstring(byte_count)
        img = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
        
        # Apply crop if exists
        if self.crop_rect:
            img = img.crop((self.crop_rect.x(), self.crop_rect.y(), 
                          self.crop_rect.x() + self.crop_rect.width(), 
                          self.crop_rect.y() + self.crop_rect.height()))
        
        # Apply rotation
        if self.rotation != 0:
            img = img.rotate(-self.rotation, expand=True)  # Negative to match Qt's rotation direction
        
        # Convert RGBA to RGB (PDF doesn't support alpha)
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
            img = background
        
        return img
    
    def get_orientation(self):
        """Get the final orientation based on settings and image dimensions"""
        if self.orientation == "auto":
            # Get current dimensions after all transformations
            img = self.get_processed_image()
            width, height = img.size
            return "landscape" if width > height else "portrait"
        return self.orientation


class ImageToPdfApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image to PDF Converter")
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Add images button
        add_images_btn = QPushButton("Add Images")
        add_images_btn.clicked.connect(self.add_images)
        
        # Generate PDF button
        generate_pdf_btn = QPushButton("Generate PDF")
        generate_pdf_btn.clicked.connect(self.generate_pdf)
        
        buttons_layout.addWidget(add_images_btn)
        buttons_layout.addWidget(generate_pdf_btn)
        
        # Scroll area for images
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Container for image items
        self.images_container = QWidget()
        self.images_layout = QVBoxLayout(self.images_container)
        self.images_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(self.images_container)
        
        # Add to main layout
        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(scroll_area)
        
        self.setCentralWidget(main_widget)
    
    def add_images(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self, "Select Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        for file_path in file_paths:
            image_item = ImageItem(file_path)
            self.images_layout.addWidget(image_item)
    
    def generate_pdf(self):
        if self.images_layout.count() == 0:
            QMessageBox.warning(self, "Warning", "No images added!")
            return
        
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", "", "PDF Files (*.pdf)"
        )
        
        if not output_path:
            return
        
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'
        
        # Process each image and prepare for PDF generation
        processed_images = []
        layout_options = []
        
        for i in range(self.images_layout.count()):
            image_item = self.images_layout.itemAt(i).widget()
            img = image_item.get_processed_image()
            
            # Create a temporary file for the processed image
            temp_path = f"temp_{i}.jpg"
            img.save(temp_path, "JPEG")
            processed_images.append(temp_path)
            
            # Get orientation for layout
            layout_options.append(img2pdf.PageOrientation.LANDSCAPE 
                                 if image_item.get_orientation() == "landscape" 
                                 else img2pdf.PageOrientation.PORTRAIT)
        
        # Generate PDF
        try:
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(processed_images, orientation=layout_options))
            
            QMessageBox.information(self, "Success", f"PDF saved to {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF: {str(e)}")
        finally:
            # Clean up temporary files
            for temp_path in processed_images:
                if os.path.exists(temp_path):
                    os.remove(temp_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageToPdfApp()
    window.show()
    sys.exit(app.exec())