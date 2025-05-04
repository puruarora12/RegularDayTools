from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QSizePolicy)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QMouseEvent


class CropDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop Image")
        self.setMinimumSize(800, 600)
        
        # Store the original pixmap
        self.original_pixmap = pixmap
        self.preview_pixmap = pixmap.scaled(
            760, 520, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Calculate scale factor for mapping crop rectangle back to original
        self.scale_x = self.original_pixmap.width() / self.preview_pixmap.width()
        self.scale_y = self.original_pixmap.height() / self.preview_pixmap.height()
        
        # Initialize crop rectangle
        self.crop_rect = QRect()
        self.start_point = QPoint()
        self.current_point = QPoint()
        self.is_cropping = False
        
        # Setup UI
        layout = QVBoxLayout(self)
        
        # Image preview label
        self.image_label = CropLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setPixmap(self.preview_pixmap)
        self.image_label.setMouseTracking(True)
        
        # Connect mouse events
        self.image_label.crop_started.connect(self.start_crop)
        self.image_label.crop_moved.connect(self.update_crop)
        self.image_label.crop_finished.connect(self.finish_crop)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        # Apply button
        apply_btn = QPushButton("Apply Crop")
        apply_btn.clicked.connect(self.accept)
        
        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_crop)
        
        # Add to layout
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(apply_btn)
        
        # Add widgets to main layout
        layout.addWidget(self.image_label)
        layout.addLayout(buttons_layout)
    
    def start_crop(self, pos):
        self.is_cropping = True
        self.start_point = pos
        self.current_point = pos
        self.update_crop_rect()
        self.update_preview()
    
    def update_crop(self, pos):
        if self.is_cropping:
            self.current_point = pos
            self.update_crop_rect()
            self.update_preview()
    
    def finish_crop(self, pos):
        self.is_cropping = False
        self.current_point = pos
        self.update_crop_rect()
        self.update_preview()
    
    def update_crop_rect(self):
        x = min(self.start_point.x(), self.current_point.x())
        y = min(self.start_point.y(), self.current_point.y())
        width = abs(self.current_point.x() - self.start_point.x())
        height = abs(self.current_point.y() - self.start_point.y())
        
        # Ensure the crop rectangle stays within the image bounds
        image_rect = self.image_label.pixmap_rect()
        
        if x < image_rect.x():
            width -= (image_rect.x() - x)
            x = image_rect.x()
        
        if y < image_rect.y():
            height -= (image_rect.y() - y)
            y = image_rect.y()
        
        if x + width > image_rect.right():
            width = image_rect.right() - x
        
        if y + height > image_rect.bottom():
            height = image_rect.bottom() - y
        
        self.crop_rect = QRect(x, y, width, height)
    
    def update_preview(self):
        # Create a copy of the preview pixmap
        preview = self.preview_pixmap.copy()
        
        # Draw the crop rectangle
        painter = QPainter(preview)
        painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
        painter.drawRect(self.crop_rect)
        painter.end()
        
        # Update the label
        self.image_label.setPixmap(preview)
    
    def reset_crop(self):
        self.is_cropping = False
        self.crop_rect = QRect()
        self.start_point = QPoint()
        self.current_point = QPoint()
        self.image_label.setPixmap(self.preview_pixmap)
    
    def get_crop_rect_for_original(self):
        """Convert preview crop rectangle to original image coordinates"""
        if self.crop_rect.isEmpty():
            return None
        
        # Adjust for pixmap position within label
        image_rect = self.image_label.pixmap_rect()
        relative_x = self.crop_rect.x() - image_rect.x()
        relative_y = self.crop_rect.y() - image_rect.y()
        
        # Scale to original pixmap size
        original_x = int(relative_x * self.scale_x)
        original_y = int(relative_y * self.scale_y)
        original_width = int(self.crop_rect.width() * self.scale_x)
        original_height = int(self.crop_rect.height() * self.scale_y)
        
        # Ensure we're within bounds of original image
        original_x = max(0, original_x)
        original_y = max(0, original_y)
        original_width = min(original_width, self.original_pixmap.width() - original_x)
        original_height = min(original_height, self.original_pixmap.height() - original_y)
        
        return QRect(original_x, original_y, original_width, original_height)


class CropLabel(QLabel):
    """Custom QLabel that handles mouse events for cropping"""
    crop_started = pyqtSignal(QPoint)
    crop_moved = pyqtSignal(QPoint)
    crop_finished = pyqtSignal(QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_rect_cache = None
    
    def pixmap_rect(self):
        """Get the rectangle where the pixmap is displayed within the label"""
        if not self.pixmap() or self.pixmap().isNull():
            return QRect()
        
        # Cache the calculated rect to avoid recalculating on every mouse move
        if self.pixmap_rect_cache is None:
            pixmap_size = self.pixmap().size()
            pixmap_size.scale(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            
            x = (self.width() - pixmap_size.width()) // 2
            y = (self.height() - pixmap_size.height()) // 2
            
            self.pixmap_rect_cache = QRect(x, y, pixmap_size.width(), pixmap_size.height())
        
        return self.pixmap_rect_cache
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reset the cache on resize
        self.pixmap_rect_cache = None
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.crop_started.emit(event.position().toPoint())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        self.crop_moved.emit(event.position().toPoint())
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.crop_finished.emit(event.position().toPoint())