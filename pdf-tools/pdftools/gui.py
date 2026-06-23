from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pdftools.compress import format_size
from pdftools.dialogs import prompt_save_pdf_path
from pdftools.dnd import DND_AVAILABLE, create_root, register_file_drop_when_ready, start_drop_polling
from pdftools.images_to_pdf import IMAGE_EXTENSIONS, PDF_EXTENSION, SUPPORTED_EXTENSIONS
from pdftools.options import PRESETS, OutputOptions
from pdftools.preview import build_preview_pages, combine_preview_pages
from pdftools.preview_gui import open_preview_dialog


class OutputOptionsPanel(ttk.LabelFrame):
    PRESET_LABELS = {
        "high": "High quality (300 DPI, light compression)",
        "balanced": "Balanced (150 DPI, recommended)",
        "small": "Small file (96 DPI, strong compression)",
        "custom": "Custom",
    }

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, text="Output quality && compression", padding=(10, 8))
        self.preset_var = tk.StringVar(value="balanced")
        self.dpi_var = tk.IntVar(value=PRESETS["balanced"].dpi)
        self.quality_var = tk.IntVar(value=PRESETS["balanced"].jpeg_quality)
        self.compress_var = tk.BooleanVar(value=PRESETS["balanced"].compress)
        self.max_dim_var = tk.IntVar(value=PRESETS["balanced"].max_image_dimension or 2400)

        preset_row = ttk.Frame(self)
        preset_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(preset_row, text="Preset:").pack(side=tk.LEFT)
        preset_combo = ttk.Combobox(
            preset_row,
            textvariable=self.preset_var,
            values=list(self.PRESET_LABELS.values()),
            state="readonly",
            width=42,
        )
        preset_combo.pack(side=tk.LEFT, padx=(8, 0))
        preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        custom = ttk.Frame(self)
        custom.pack(fill=tk.X)
        self.custom_frame = custom

        ttk.Label(custom, text="DPI:").grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        self.dpi_spin = ttk.Spinbox(custom, from_=72, to=600, textvariable=self.dpi_var, width=6)
        self.dpi_spin.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(custom, text="JPEG quality:").grid(row=0, column=2, sticky=tk.W, padx=(16, 6))
        self.quality_spin = ttk.Spinbox(
            custom,
            from_=1,
            to=100,
            textvariable=self.quality_var,
            width=6,
        )
        self.quality_spin.grid(row=0, column=3, sticky=tk.W)

        ttk.Label(custom, text="Max image px:").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        self.max_dim_spin = ttk.Spinbox(
            custom,
            from_=256,
            to=8000,
            increment=100,
            textvariable=self.max_dim_var,
            width=8,
        )
        self.max_dim_spin.grid(row=1, column=1, sticky=tk.W, pady=(6, 0))

        self.compress_check = ttk.Checkbutton(
            custom,
            text="Compress PDF streams",
            variable=self.compress_var,
        )
        self.compress_check.grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=(16, 0), pady=(6, 0))

        self._apply_preset("balanced", lock_custom=True)

    def _label_to_key(self, label: str) -> str:
        for key, value in self.PRESET_LABELS.items():
            if value == label:
                return key
        return "balanced"

    def _on_preset_change(self, _event=None) -> None:
        key = self._label_to_key(self.preset_var.get())
        if key == "custom":
            self._set_custom_enabled(True)
            return
        self._apply_preset(key, lock_custom=True)

    def _apply_preset(self, key: str, lock_custom: bool) -> None:
        preset = PRESETS[key]
        self.dpi_var.set(preset.dpi)
        self.quality_var.set(preset.jpeg_quality)
        self.compress_var.set(preset.compress)
        self.max_dim_var.set(preset.max_image_dimension or 8000)
        self._set_custom_enabled(not lock_custom)

    def _set_custom_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in (self.dpi_spin, self.quality_spin, self.max_dim_spin, self.compress_check):
            widget.configure(state=state)

    def get_options(self) -> OutputOptions:
        key = self._label_to_key(self.preset_var.get())
        if key != "custom":
            return PRESETS[key]

        max_dim = int(self.max_dim_var.get())
        return OutputOptions(
            dpi=int(self.dpi_var.get()),
            jpeg_quality=int(self.quality_var.get()),
            compress=bool(self.compress_var.get()),
            max_image_dimension=None if max_dim >= 8000 else max_dim,
        )


class OrderedFilePanel(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
        add_label: str,
        filetypes: list[tuple[str, str]],
        action_label: str,
        on_convert,
        empty_hint: str,
        show_type_tags: bool = False,
        accepted_extensions: set[str] | None = None,
    ) -> None:
        super().__init__(master, padding=12)
        self.filetypes = filetypes
        self.on_convert = on_convert
        self.empty_hint = empty_hint
        self.show_type_tags = show_type_tags
        self.accepted_extensions = accepted_extensions
        self.files: list[Path] = []
        self._set_status = lambda _message: None

        ttk.Label(self, text=title).pack(anchor=tk.W)
        drop_hint = "Drag and drop files here, or use Add Files."
        if not DND_AVAILABLE:
            drop_hint = "Use Add Files to select input files."
        ttk.Label(self, text=drop_hint, foreground="#555").pack(anchor=tk.W, pady=(2, 6))

        list_frame = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_list = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            activestyle="none",
            bd=0,
            highlightthickness=0,
        )
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_list.yview)

        self._register_drop_targets(list_frame)

        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(btn_row, text=add_label, command=self.add_files).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Remove", command=self.remove_selected).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_row, text="Move Up", command=lambda: self.move_selected(-1)).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_row, text="Move Down", command=lambda: self.move_selected(1)).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btn_row, text="Clear", command=self.clear_files).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Button(self, text=action_label, command=self.save).pack(anchor=tk.W)

    def _register_drop_targets(self, list_frame: tk.Frame) -> None:
        register_file_drop_when_ready(
            self.file_list,
            self.add_paths,
            accepted_extensions=self.accepted_extensions,
        )

    def add_paths(self, paths: list[Path]) -> None:
        added = 0
        for path in paths:
            if not path.is_file():
                continue
            if self.accepted_extensions is not None and path.suffix.lower() not in self.accepted_extensions:
                continue
            if path not in self.files:
                self.files.append(path)
                added += 1

        if added == 0:
            return

        self._refresh_list()
        self._set_status(f"Added {added} file(s). Total: {len(self.files)}.")

    def set_status(self, callback) -> None:
        self._set_status = callback

    def _refresh_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.files:
            label = path.name
            if self.show_type_tags:
                suffix = path.suffix.lower()
                if suffix == ".pdf":
                    label = f"[PDF] {label}"
                elif suffix in IMAGE_EXTENSIONS:
                    label = f"[IMG] {label}"
            self.file_list.insert(tk.END, label)

    def add_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Select files", filetypes=self.filetypes)
        if not selected:
            return
        self.add_paths([Path(raw_path) for raw_path in selected])

    def remove_selected(self) -> None:
        indices = list(self.file_list.curselection())
        if not indices:
            return

        for index in reversed(indices):
            del self.files[index]

        self._refresh_list()
        self._set_status(f"{len(self.files)} file(s) remaining.")

    def move_selected(self, direction: int) -> None:
        indices = list(self.file_list.curselection())
        if len(indices) != 1:
            messagebox.showinfo("Move file", "Select exactly one file to move.")
            return

        index = indices[0]
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.files):
            return

        self.files[index], self.files[new_index] = self.files[new_index], self.files[index]
        self._refresh_list()
        self.file_list.selection_set(new_index)

    def clear_files(self) -> None:
        self.files.clear()
        self._refresh_list()
        self._set_status("List cleared.")

    def save(self) -> None:
        if not self.files:
            messagebox.showwarning("No files", self.empty_hint)
            return
        self.on_convert(self.files)


class CompressPanel(ttk.Frame):
    def __init__(self, master: tk.Misc, *, on_compress) -> None:
        super().__init__(master, padding=12)
        self.on_compress = on_compress
        self.input_path: Path | None = None
        self._set_status = lambda _message: None

        ttk.Label(
            self,
            text="Select an existing PDF and re-save it with compression settings.",
        ).pack(anchor=tk.W)

        drop_hint = "Drag and drop a PDF here, or use Choose PDF."
        if not DND_AVAILABLE:
            drop_hint = "Use Choose PDF to select a file."
        ttk.Label(self, text=drop_hint, foreground="#555").pack(anchor=tk.W, pady=(4, 0))

        self.drop_zone = tk.LabelFrame(self, text="Selected PDF", padx=10, pady=10)
        self.drop_zone.pack(fill=tk.X, pady=(10, 8))

        path_row = tk.Frame(self.drop_zone)
        path_row.pack(fill=tk.X)
        self.path_label = ttk.Label(path_row, text="No file selected.", foreground="#444")
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_row, text="Choose PDF...", command=self.choose_file).pack(side=tk.RIGHT)

        register_file_drop_when_ready(
            self.drop_zone,
            self._set_input_paths,
            accepted_extensions={PDF_EXTENSION},
        )

        ttk.Button(self, text="Preview && Save...", command=self.compress).pack(anchor=tk.W)

    def set_status(self, callback) -> None:
        self._set_status = callback

    def _set_input_paths(self, paths: list[Path]) -> None:
        pdf_paths = [
            path for path in paths if path.is_file() and path.suffix.lower() == PDF_EXTENSION
        ]
        if not pdf_paths:
            return
        self.input_path = pdf_paths[0]
        self.path_label.config(text=str(self.input_path))
        self._set_status(f"Selected {self.input_path.name}.")

    def choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select PDF to compress",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not selected:
            return
        self._set_input_paths([Path(selected)])

    def compress(self) -> None:
        if self.input_path is None:
            messagebox.showwarning("No file", "Choose a PDF file first.")
            return
        self.on_compress(self.input_path)


class PdfToolsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF Tools")
        self.root.minsize(620, 580)
        self.root.geometry("720x640")
        self._last_output_dir: Path | None = None

        self.options_panel = OutputOptionsPanel(root)
        self.options_panel.pack(fill=tk.X, padx=12, pady=(12, 0))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        image_pattern = ";".join(f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS))
        combine_types = [
            ("PDF and image files", f"*.pdf;{image_pattern}"),
            ("PDF files", "*.pdf"),
            ("Image files", image_pattern),
            ("All files", "*.*"),
        ]

        self.merge_panel = OrderedFilePanel(
            self.notebook,
            title="Files (top to bottom = page order). PDFs and images can be mixed:",
            add_label="Add Files...",
            filetypes=combine_types,
            action_label="Preview && Save...",
            on_convert=self._merge_files,
            empty_hint="Add at least one PDF or image file.",
            show_type_tags=True,
            accepted_extensions=SUPPORTED_EXTENSIONS,
        )
        self.notebook.add(self.merge_panel, text="Combine PDFs")

        image_types = [
            ("Image files", image_pattern),
            ("All files", "*.*"),
        ]
        self.images_panel = OrderedFilePanel(
            self.notebook,
            title="Images (top to bottom = page order):",
            add_label="Add Images...",
            filetypes=image_types,
            action_label="Preview && Save...",
            on_convert=self._convert_images,
            empty_hint="Add at least one image file.",
            accepted_extensions=IMAGE_EXTENSIONS,
        )
        self.notebook.add(self.images_panel, text="Images to PDF")

        self.compress_panel = CompressPanel(self.notebook, on_compress=self._compress_pdf)
        self.notebook.add(self.compress_panel, text="Compress PDF")

        self._register_window_drop()

        footer = ttk.Frame(root, padding=(12, 0, 12, 12))
        footer.pack(fill=tk.X)

        self.status = ttk.Label(footer, text="Choose a tab to get started.", foreground="#444")
        self.status.pack(side=tk.LEFT)

        ttk.Button(footer, text="Quit", command=root.destroy).pack(side=tk.RIGHT)

        self.merge_panel.set_status(self._set_status)
        self.images_panel.set_status(self._set_status)
        self.compress_panel.set_status(self._set_status)

    def _set_status(self, message: str) -> None:
        self.status.config(text=message)

    def _register_window_drop(self) -> None:
        def route_drop(paths: list[Path]) -> None:
            tab_id = self.notebook.index(self.notebook.select())
            if tab_id == 0:
                self.merge_panel.add_paths(paths)
            elif tab_id == 1:
                self.images_panel.add_paths(paths)
            elif tab_id == 2:
                self.compress_panel._set_input_paths(paths)

        register_file_drop_when_ready(self.root, route_drop)

    def _size_summary(self, before: int | None, after: int) -> str:
        if before is None:
            return f"Output size: {format_size(after)}"
        if before <= 0:
            return f"Output size: {format_size(after)}"
        saved = max(0, before - after)
        pct = (saved / before * 100) if before else 0
        return f"Size: {format_size(before)} -> {format_size(after)} ({pct:.0f}% smaller)"

    def _merge_files(self, files: list[Path]) -> None:
        try:
            pages = build_preview_pages(files)
        except Exception as exc:
            messagebox.showerror("Preview failed", str(exc))
            self._set_status(f"Error: {exc}")
            return

        reviewed = open_preview_dialog(self.root, pages, title="Preview combined PDF")
        if reviewed is None:
            return

        output_path, output_dir = prompt_save_pdf_path(
            title="Save combined PDF as",
            initialfile="combined.pdf",
            last_dir=self._last_output_dir,
            input_paths=files,
        )
        if output_path is None:
            return

        options = self.options_panel.get_options()
        before = sum(path.stat().st_size for path in files if path.is_file())

        try:
            page_count = combine_preview_pages(reviewed, output_path, options)
            after = output_path.stat().st_size
        except Exception as exc:
            messagebox.showerror("Combine failed", str(exc))
            self._set_status(f"Error: {exc}")
            return

        self._last_output_dir = output_dir
        self._set_status(f"Saved {output_path.name} ({page_count} pages). {self._size_summary(before, after)}")
        messagebox.showinfo(
            "Success",
            f"Combined {len(files)} file(s) into:\n{output_path}\n\n"
            f"Pages: {page_count}\n{self._size_summary(before, after)}",
        )

    def _convert_images(self, files: list[Path]) -> None:
        try:
            pages = build_preview_pages(files)
        except Exception as exc:
            messagebox.showerror("Preview failed", str(exc))
            self._set_status(f"Error: {exc}")
            return

        reviewed = open_preview_dialog(self.root, pages, title="Preview images as PDF")
        if reviewed is None:
            return

        output_path, output_dir = prompt_save_pdf_path(
            title="Save PDF as",
            initialfile="from_images.pdf",
            last_dir=self._last_output_dir,
            input_paths=files,
        )
        if output_path is None:
            return

        options = self.options_panel.get_options()
        before = sum(path.stat().st_size for path in files if path.is_file())

        try:
            page_count = combine_preview_pages(reviewed, output_path, options)
            after = output_path.stat().st_size
        except Exception as exc:
            messagebox.showerror("Conversion failed", str(exc))
            self._set_status(f"Error: {exc}")
            return

        self._last_output_dir = output_dir
        self._set_status(f"Saved {output_path.name} ({page_count} pages). {self._size_summary(before, after)}")
        messagebox.showinfo(
            "Success",
            f"Converted {len(files)} image(s) into:\n{output_path}\n\n"
            f"Pages: {page_count}\n{self._size_summary(before, after)}",
        )

    def _compress_pdf(self, input_path: Path) -> None:
        try:
            pages = build_preview_pages([input_path])
        except Exception as exc:
            messagebox.showerror("Preview failed", str(exc))
            self._set_status(f"Error: {exc}")
            return

        reviewed = open_preview_dialog(self.root, pages, title="Preview PDF before compressing")
        if reviewed is None:
            return

        output_path, output_dir = prompt_save_pdf_path(
            title="Save compressed PDF as",
            initialfile=f"{input_path.stem}_compressed.pdf",
            last_dir=self._last_output_dir,
            input_paths=[input_path],
        )
        if output_path is None:
            return

        options = self.options_panel.get_options()
        before = input_path.stat().st_size

        try:
            page_count = combine_preview_pages(reviewed, output_path, options)
            after = output_path.stat().st_size
        except Exception as exc:
            messagebox.showerror("Compression failed", str(exc))
            self._set_status(f"Error: {exc}")
            return

        self._last_output_dir = output_dir
        self._set_status(f"Saved {output_path.name}. {self._size_summary(before, after)}")
        messagebox.showinfo(
            "Success",
            f"Compressed PDF saved to:\n{output_path}\n\n"
            f"Pages: {page_count}\n{self._size_summary(before, after)}",
        )


def run_gui() -> None:
    root = create_root()
    start_drop_polling(root)
    PdfToolsApp(root)
    root.mainloop()
