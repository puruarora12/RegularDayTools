from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from pdftools.preview import PreviewPage, render_preview_image


class PreviewDialog(tk.Toplevel):
    CANVAS_PADDING = 16

    def __init__(self, parent: tk.Misc, pages: list[PreviewPage], *, title: str) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("1120x820")
        self.minsize(920, 700)
        self.transient(parent)
        self.grab_set()

        self.pages = pages
        self.current_index = 0
        self.result: list[PreviewPage] | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._preview_job: str | None = None
        self._last_preview_size = (0, 0)

        self._build_ui()
        self._center_on_parent(parent)
        self._select_page(0)
        self.after_idle(self._update_preview)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Left>", lambda _event: self._show_previous())
        self.bind("<Right>", lambda _event: self._show_next())
        self.bind("<Control-s>", lambda _event: self._save())

    def _center_on_parent(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        parent.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        ttk.Label(
            main,
            text="Review each page, rotate if needed, then save.",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        body = ttk.Frame(main)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Pages").grid(row=0, column=0, sticky="w")

        list_frame = ttk.Frame(left)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.page_list = tk.Listbox(
            list_frame,
            width=32,
            exportselection=False,
            activestyle="none",
        )
        self.page_list.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, command=self.page_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.page_list.config(yscrollcommand=scrollbar.set)
        self.page_list.bind("<<ListboxSelect>>", self._on_list_select)

        order_row = ttk.Frame(left)
        order_row.grid(row=2, column=0, sticky="ew")
        ttk.Button(order_row, text="Move Up", command=lambda: self._move_page(-1)).pack(side=tk.LEFT)
        ttk.Button(order_row, text="Move Down", command=lambda: self._move_page(1)).pack(side=tk.LEFT, padx=(6, 0))

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        preview_frame = ttk.LabelFrame(right, text="Preview", padding=8)
        preview_frame.grid(row=0, column=0, sticky="nsew")
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg="#ececec",
            highlightthickness=1,
            highlightbackground="#999999",
        )
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)

        controls = ttk.Frame(main)
        controls.grid(row=2, column=0, sticky="ew", pady=(12, 8))

        ttk.Button(controls, text="Previous", command=self._show_previous).pack(side=tk.LEFT)
        ttk.Button(controls, text="Next", command=self._show_next).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(controls, text="Rotate Left", command=self._rotate_left).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Button(controls, text="Rotate Right", command=self._rotate_right).pack(side=tk.LEFT, padx=(6, 0))

        self.page_info = ttk.Label(controls, text="")
        self.page_info.pack(side=tk.RIGHT)

        actions = ttk.Frame(main)
        actions.grid(row=3, column=0, sticky="ew")
        ttk.Button(actions, text="Save...", command=self._save).pack(side=tk.LEFT)
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(side=tk.RIGHT)

        self._refresh_page_list()

    def _canvas_fit_size(self) -> tuple[int, int]:
        self.preview_canvas.update_idletasks()
        width = self.preview_canvas.winfo_width()
        height = self.preview_canvas.winfo_height()
        pad = self.CANVAS_PADDING * 2
        return (
            max(width - pad, 1),
            max(height - pad, 1),
        )

    def _on_canvas_resize(self, event) -> None:
        if event.widget is not self.preview_canvas:
            return
        if event.width < 80 or event.height < 80:
            return
        size = (event.width, event.height)
        if size == self._last_preview_size:
            return
        self._last_preview_size = size
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(120, self._update_preview)

    def _refresh_page_list(self) -> None:
        selection = self.current_index
        self.page_list.delete(0, tk.END)
        for index, page in enumerate(self.pages):
            self.page_list.insert(tk.END, page.list_label(index))
        if self.pages:
            self.page_list.selection_clear(0, tk.END)
            self.page_list.selection_set(selection)
            self.page_list.see(selection)

    def _on_list_select(self, _event=None) -> None:
        selection = self.page_list.curselection()
        if not selection:
            return
        self.current_index = selection[0]
        self._update_preview()

    def _select_page(self, index: int) -> None:
        if not self.pages:
            return
        self.current_index = max(0, min(index, len(self.pages) - 1))
        self._refresh_page_list()
        self._update_preview()

    def _draw_preview_image(self, image) -> None:
        self._photo = ImageTk.PhotoImage(image)
        self.preview_canvas.delete("all")
        canvas_width = max(self.preview_canvas.winfo_width(), 1)
        canvas_height = max(self.preview_canvas.winfo_height(), 1)
        self.preview_canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self._photo,
            anchor=tk.CENTER,
        )

    def _draw_preview_message(self, message: str) -> None:
        self._photo = None
        self.preview_canvas.delete("all")
        canvas_width = max(self.preview_canvas.winfo_width(), 1)
        canvas_height = max(self.preview_canvas.winfo_height(), 1)
        self.preview_canvas.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text=message,
            anchor=tk.CENTER,
            fill="#333333",
            width=max(canvas_width - 40, 200),
        )

    def _update_preview(self) -> None:
        self._preview_job = None
        if not self.pages:
            self._draw_preview_message("No pages to preview.")
            return

        page = self.pages[self.current_index]
        self.page_info.config(text=f"Page {self.current_index + 1} of {len(self.pages)}")

        try:
            image = render_preview_image(page, fit_size=self._canvas_fit_size())
        except Exception as exc:
            self._draw_preview_message(f"Preview failed:\n{exc}")
            return

        self._draw_preview_image(image)
        image.close()

    def _show_previous(self) -> None:
        if self.current_index > 0:
            self._select_page(self.current_index - 1)

    def _show_next(self) -> None:
        if self.current_index < len(self.pages) - 1:
            self._select_page(self.current_index + 1)

    def _rotate_left(self) -> None:
        if not self.pages:
            return
        self.pages[self.current_index].rotate_left()
        self._refresh_page_list()
        self._update_preview()

    def _rotate_right(self) -> None:
        if not self.pages:
            return
        self.pages[self.current_index].rotate_right()
        self._refresh_page_list()
        self._update_preview()

    def _move_page(self, direction: int) -> None:
        index = self.current_index
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.pages):
            return
        self.pages[index], self.pages[new_index] = self.pages[new_index], self.pages[index]
        self._select_page(new_index)

    def _save(self) -> None:
        self.result = self.pages
        self.grab_release()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.grab_release()
        self.destroy()

    def show(self) -> list[PreviewPage] | None:
        self.wait_window()
        return self.result


def open_preview_dialog(
    parent: tk.Misc,
    pages: list[PreviewPage],
    *,
    title: str = "Preview before save",
) -> list[PreviewPage] | None:
    dialog = PreviewDialog(parent, pages, title=title)
    return dialog.show()
