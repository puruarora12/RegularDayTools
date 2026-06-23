from __future__ import annotations

import queue
import sys
import time
from collections.abc import Callable
from pathlib import Path

WINDND_AVAILABLE = False
TKDND_AVAILABLE = False
DND_FILES = None
TkinterDnD = None

if sys.platform == "win32":
    try:
        import windnd

        WINDND_AVAILABLE = True
    except ImportError:
        windnd = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    TKDND_AVAILABLE = True
except ImportError:
    pass

DND_AVAILABLE = WINDND_AVAILABLE or TKDND_AVAILABLE

_HOOKED_WIDGETS: set[int] = set()
_WIDGET_HANDLERS: dict[int, list[int]] = {}
_HANDLERS: dict[int, tuple[Callable[[list[Path]], None], set[str] | None]] = {}
_HANDLER_SEQ = 0
_DROP_QUEUE: queue.SimpleQueue[tuple[int, object]] = queue.SimpleQueue()
_RECENT_DROP_KEYS: dict[str, float] = {}
_DROP_DEDUPE_SECONDS = 0.25
_POLL_INTERVAL_MS = 50


def create_root():
    if TKDND_AVAILABLE and TkinterDnD is not None and not WINDND_AVAILABLE:
        return TkinterDnD.Tk()
    import tkinter as tk

    return tk.Tk()


def decode_dropped_files(raw_files) -> list[str]:
    if raw_files is None:
        return []

    items = raw_files if isinstance(raw_files, (list, tuple)) else [raw_files]
    paths: list[str] = []

    for item in items:
        if isinstance(item, bytes):
            try:
                text = item.decode("utf-8")
            except UnicodeDecodeError:
                text = item.decode("mbcs")
        else:
            text = str(item)
        text = text.strip().strip('"')
        if text:
            paths.append(text)

    return paths


def _filter_paths(paths: list[Path], accepted_extensions: set[str] | None) -> list[Path]:
    if accepted_extensions is None:
        return [path for path in paths if path.is_file()]

    return [
        path
        for path in paths
        if path.is_file() and path.suffix.lower() in accepted_extensions
    ]


def _should_handle_drop(path_strings: list[str]) -> bool:
    if not path_strings:
        return False

    drop_key = "|".join(sorted(path_strings))
    now = time.monotonic()
    last_seen = _RECENT_DROP_KEYS.get(drop_key)
    if last_seen is not None and now - last_seen < _DROP_DEDUPE_SECONDS:
        return False

    _RECENT_DROP_KEYS[drop_key] = now
    return True


def _alloc_handler(
    on_paths: Callable[[list[Path]], None],
    accepted_extensions: set[str] | None,
) -> int:
    global _HANDLER_SEQ
    _HANDLER_SEQ += 1
    handler_id = _HANDLER_SEQ
    _HANDLERS[handler_id] = (on_paths, accepted_extensions)
    return handler_id


def _enqueue_drop(handler_id: int, raw_files: object) -> None:
    # windnd may call this from a Windows thread — queue only, no Tk calls.
    _DROP_QUEUE.put((handler_id, raw_files))


def _process_drop_queue() -> None:
    while True:
        try:
            handler_id, raw_files = _DROP_QUEUE.get_nowait()
        except queue.Empty:
            break

        handler = _HANDLERS.get(handler_id)
        if handler is None:
            continue

        on_paths, accepted_extensions = handler
        path_strings = decode_dropped_files(raw_files)
        if not _should_handle_drop(path_strings):
            continue

        try:
            paths = _filter_paths([Path(text) for text in path_strings], accepted_extensions)
            if paths:
                on_paths(paths)
        except Exception:
            continue


def start_drop_polling(root) -> None:
    if not WINDND_AVAILABLE:
        return

    def poll() -> None:
        _process_drop_queue()
        try:
            root.after(_POLL_INTERVAL_MS, poll)
        except Exception:
            return

    root.after(_POLL_INTERVAL_MS, poll)


def _register_windnd(
    widget,
    on_paths: Callable[[list[Path]], None],
    *,
    accepted_extensions: set[str] | None,
) -> bool:
    if not WINDND_AVAILABLE or windnd is None:
        return False

    handler_id = _alloc_handler(on_paths, accepted_extensions)

    try:
        widget.update_idletasks()
        widget_id = widget.winfo_id()
    except Exception:
        _HANDLERS.pop(handler_id, None)
        return False

    _WIDGET_HANDLERS.setdefault(widget_id, []).append(handler_id)

    if widget_id in _HOOKED_WIDGETS:
        return True

    def handle_drop(raw_files) -> None:
        for queued_handler_id in _WIDGET_HANDLERS.get(widget_id, []):
            _enqueue_drop(queued_handler_id, raw_files)

    try:
        windnd.hook_dropfiles(widget, func=handle_drop)
    except Exception:
        _HANDLERS.pop(handler_id, None)
        _WIDGET_HANDLERS[widget_id].remove(handler_id)
        return False

    _HOOKED_WIDGETS.add(widget_id)
    return True


def _register_tkdnd(
    widget,
    on_paths: Callable[[list[Path]], None],
    *,
    accepted_extensions: set[str] | None,
) -> bool:
    if not TKDND_AVAILABLE or DND_FILES is None:
        return False

    handler_id = _alloc_handler(on_paths, accepted_extensions)

    def handle_drop(event) -> None:
        _enqueue_drop(handler_id, widget.tk.splitlist(event.data))

    widget.drop_target_register(DND_FILES)
    widget.dnd_bind("<<Drop>>", handle_drop)
    return True


def register_file_drop(
    widget,
    on_paths: Callable[[list[Path]], None],
    *,
    accepted_extensions: set[str] | None = None,
) -> bool:
    if WINDND_AVAILABLE:
        return _register_windnd(widget, on_paths, accepted_extensions=accepted_extensions)
    return _register_tkdnd(widget, on_paths, accepted_extensions=accepted_extensions)


def register_file_drop_when_ready(
    widget,
    on_paths: Callable[[list[Path]], None],
    *,
    accepted_extensions: set[str] | None = None,
) -> None:
    def _hook() -> None:
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return
        register_file_drop(widget, on_paths, accepted_extensions=accepted_extensions)

    try:
        widget.after_idle(_hook)
    except Exception:
        return
