import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import img2pdf
import tempfile

class ImageItem(ttk.Frame):
    def __init__(self, master, image_path, on_delete=None, on_move_up=None, on_move_down=None):
        super().__init__(master, padding=10, relief="ridge", borderwidth=1)
        self.image_path = image_path
        self.rotation = 0
        self.orientation = "auto"
        self.crop_box = None  # (left, upper, right, lower)
        self.on_delete = on_delete
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        
        # Load the image
        self.original_image = Image.open(image_path)
        self.display_image = self.original_image.copy()
        self.update_display_image()
        
        # Create UI components
        self.create_widgets()
        
    def create_widgets(self):
        # Image preview
        self.preview_frame = ttk.Frame(self)
        self.preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        
        self.image_label = ttk.Label(self.preview_frame)
        self.image_label.pack(expand=True)
        self.update_preview()
        
        # Controls
        controls_frame = ttk.Frame(self)
        controls_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        # Rotation buttons
        rotate_left_btn = ttk.Button(controls_frame, text="↺", width=3, 
                                   command=lambda: self.rotate(-90))
        rotate_left_btn.pack(side=tk.LEFT, padx=2)
        
        rotate_right_btn = ttk.Button(controls_frame, text="↻", width=3,
                                    command=lambda: self.rotate(90))
        rotate_right_btn.pack(side=tk.LEFT, padx=2)
        
        # Orientation dropdown
        self.orientation_var = tk.StringVar(value="Auto")
        orientation_combo = ttk.Combobox(controls_frame, textvariable=self.orientation_var,
                                       values=["Auto", "Portrait", "Landscape"], width=8)
        orientation_combo.pack(side=tk.LEFT, padx=2)
        orientation_combo.bind("<<ComboboxSelected>>", self.set_orientation)
        
        # Crop button
        crop_btn = ttk.Button(controls_frame, text="Crop", width=5,
                            command=self.crop_image)
        crop_btn.pack(side=tk.LEFT, padx=2)
        
        # Reset crop button
        reset_crop_btn = ttk.Button(controls_frame, text="Reset Crop", width=8,
                                  command=self.reset_crop)
        reset_crop_btn.pack(side=tk.LEFT, padx=2)
        
        # Move buttons
        move_up_btn = ttk.Button(controls_frame, text="↑", width=3,
                               command=self.move_up)
        move_up_btn.pack(side=tk.LEFT, padx=2)
        
        move_down_btn = ttk.Button(controls_frame, text="↓", width=3,
                                 command=self.move_down)
        move_down_btn.pack(side=tk.LEFT, padx=2)
        
        # Delete button
        delete_btn = ttk.Button(controls_frame, text="Delete", width=5,
                              command=self.delete_item)
        delete_btn.pack(side=tk.LEFT, padx=2)
        
    def update_display_image(self):
        img = self.original_image.copy()
        
        # Apply crop if exists
        if self.crop_box:
            img = img.crop(self.crop_box)
        
        # Apply rotation
        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)
        
        self.display_image = img
        
    def update_preview(self):
        # Resize for preview (maintaining aspect ratio)
        img = self.display_image.copy()
        img.thumbnail((200, 200))
        
        # Convert to PhotoImage and keep a reference
        self.tk_image = ImageTk.PhotoImage(img)
        self.image_label.config(image=self.tk_image)
        
    def rotate(self, degrees):
        self.rotation = (self.rotation + degrees) % 360
        self.update_display_image()
        self.update_preview()
        
    def set_orientation(self, event=None):
        self.orientation = self.orientation_var.get().lower()
        
    def crop_image(self):
        # Open a new window for cropping
        crop_window = tk.Toplevel(self)
        crop_window.title("Crop Image")
        crop_window.geometry("800x600")
        
        # Make a copy of the image for cropping (with rotation applied)
        img = self.original_image.copy()
        if self.rotation != 0:
            img = img.rotate(self.rotation, expand=True)
        
        # Resize for display
        display_img = img.copy()
        display_img.thumbnail((700, 500))
        
        # Calculate scale factors
        scale_x = img.width / display_img.width
        scale_y = img.height / display_img.height
        
        # Create a canvas to display the image and draw the crop rectangle
        canvas = tk.Canvas(crop_window, width=display_img.width, height=display_img.height)
        canvas.pack(pady=10)
        
        # Convert to PhotoImage and keep a reference
        self.crop_tk_image = ImageTk.PhotoImage(display_img)
        canvas.create_image(0, 0, anchor=tk.NW, image=self.crop_tk_image)
        
        # Variables for the crop rectangle
        start_x = start_y = 0
        rect_id = None
        crop_rect = [0, 0, 0, 0]  # [start_x, start_y, end_x, end_y]
        
        def start_crop(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, 
                                           outline="red", width=2, dash=(4, 4))
                
        def drag_crop(event):
            nonlocal rect_id
            if rect_id:
                # Keep within canvas bounds
                x = min(max(0, event.x), display_img.width)
                y = min(max(0, event.y), display_img.height)
                canvas.coords(rect_id, start_x, start_y, x, y)
                
        def end_crop(event):
            nonlocal crop_rect
            # Get the final rectangle coordinates
            coords = canvas.coords(rect_id)
            # Convert to image coordinates in the correct order (left, upper, right, lower)
            crop_rect = [
                min(int(coords[0]), int(coords[2])),
                min(int(coords[1]), int(coords[3])),
                max(int(coords[0]), int(coords[2])),
                max(int(coords[1]), int(coords[3]))
            ]
            
        # Bind mouse events
        canvas.bind("<ButtonPress-1>", start_crop)
        canvas.bind("<B1-Motion>", drag_crop)
        canvas.bind("<ButtonRelease-1>", end_crop)
        
        # Buttons frame
        btn_frame = ttk.Frame(crop_window)
        btn_frame.pack(pady=10)
        
        def apply_crop():
            # Scale the crop rectangle to the original image size
            if crop_rect[2] > crop_rect[0] and crop_rect[3] > crop_rect[1]:  # Valid crop
                scaled_crop = [
                    int(crop_rect[0] * scale_x),
                    int(crop_rect[1] * scale_y),
                    int(crop_rect[2] * scale_x),
                    int(crop_rect[3] * scale_y)
                ]
                self.crop_box = tuple(scaled_crop)
                self.update_display_image()
                self.update_preview()
            crop_window.destroy()
            
        def cancel_crop():
            crop_window.destroy()
            
        # Add buttons
        apply_btn = ttk.Button(btn_frame, text="Apply Crop", command=apply_crop)
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=cancel_crop)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
    def reset_crop(self):
        self.crop_box = None
        self.update_display_image()
        self.update_preview()
        
    def delete_item(self):
        if self.on_delete:
            self.on_delete(self)
        
    def move_up(self):
        if self.on_move_up:
            self.on_move_up(self)
            
    def move_down(self):
        if self.on_move_down:
            self.on_move_down(self)
            
    def get_processed_image(self):
        """Return a PIL Image with all modifications applied"""
        return self.display_image
        
    def get_orientation(self):
        """Get the final orientation based on settings and image dimensions"""
        if self.orientation == "auto":
            width, height = self.display_image.size
            return "landscape" if width > height else "portrait"
        return self.orientation


class ImageToPdfApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to PDF Converter")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Configure style
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TButton', background='#e1e1e1', font=('Arial', 10))
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        
        # Main frame
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Add images button
        add_btn = ttk.Button(buttons_frame, text="Add Images", command=self.add_images)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # Generate PDF button
        gen_btn = ttk.Button(buttons_frame, text="Generate PDF", command=self.generate_pdf)
        gen_btn.pack(side=tk.LEFT, padx=5)
        
        # Images container with scrollbar
        self.canvas = tk.Canvas(main_frame, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=880)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # List to keep track of image items
        self.image_items = []
        
    def add_images(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        
        if not file_paths:
            return
            
        for path in file_paths:
            self.add_image_item(path)
            
        # Update the scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
    def add_image_item(self, path):
        item = ImageItem(
            self.scrollable_frame, 
            path,
            on_delete=self.remove_image_item,
            on_move_up=self.move_item_up,
            on_move_down=self.move_item_down
        )
        item.pack(fill=tk.X, pady=5, padx=5)
        self.image_items.append(item)
            
    def remove_image_item(self, item):
        item.pack_forget()
        self.image_items.remove(item)
        
    def move_item_up(self, item):
        idx = self.image_items.index(item)
        if idx > 0:
            # Swap items in the list
            self.image_items[idx], self.image_items[idx-1] = self.image_items[idx-1], self.image_items[idx]
            # Repack all items in the new order
            self.repack_items()
            
    def move_item_down(self, item):
        idx = self.image_items.index(item)
        if idx < len(self.image_items) - 1:
            # Swap items in the list
            self.image_items[idx], self.image_items[idx+1] = self.image_items[idx+1], self.image_items[idx]
            # Repack all items in the new order
            self.repack_items()
            
    def repack_items(self):
        for item in self.image_items:
            item.pack_forget()
        for item in self.image_items:
            item.pack(fill=tk.X, pady=5, padx=5)
            
    def generate_pdf(self):
        if not self.image_items:
            messagebox.showwarning("Warning", "No images added!")
            return
            
        output_path = filedialog.asksaveasfilename(
            title="Save PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if not output_path:
            return
            
        # Process each image and prepare for PDF generation
        processed_images = []
        layout_options = []
        
        # Create temporary directory for processed images
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                for i, item in enumerate(self.image_items):
                    img = item.get_processed_image()
                    
                    # Convert to RGB if needed (PDF doesn't support alpha)
                    if img.mode == 'RGBA':
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    
                    # Save processed image to temp file
                    temp_path = os.path.join(temp_dir, f"temp_{i}.jpg")
                    img.save(temp_path, "JPEG")
                    processed_images.append(temp_path)
                    
                    # Get orientation for layout
                    layout_options.append(
                        img2pdf.PageOrientation.LANDSCAPE 
                        if item.get_orientation() == "landscape" 
                        else img2pdf.PageOrientation.portrait
                    )
                
                # Generate PDF
                with open(output_path, "wb") as f:
                    f.write(img2pdf.convert(processed_images, orientation=layout_options))
                
                messagebox.showinfo("Success", f"PDF saved to {output_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate PDF: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToPdfApp(root)
    root.mainloop()