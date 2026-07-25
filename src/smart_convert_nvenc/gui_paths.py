from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tkinter import filedialog, messagebox

from .paths import CoursePaths, resolve_course_paths
from .temp_paths import cleanup_conversion_temps

if TYPE_CHECKING:
    from .gui import App


def busy(app: App) -> bool:
    return bool(app._worker and app._worker.is_alive())


def browse_folder(app: App, title: str, current: str) -> Path | None:
    initial = current if Path(current).is_dir() else str(Path.home())
    chosen = filedialog.askdirectory(title=title, initialdir=initial, mustexist=True)
    if not chosen:
        return None
    return Path(chosen)


def browse_inbox(app: App) -> None:
    path = browse_folder(app, "Select inbox folder", app.inbox_var.get())
    if path:
        app.inbox_var.set(str(path.resolve()))


def browse_outbox(app: App) -> None:
    path = browse_folder(app, "Select outbox folder", app.outbox_var.get())
    if path:
        app.outbox_var.set(str(path.resolve()))


def browse_tmp(app: App) -> None:
    path = browse_folder(app, "Select tmp folder", app.tmp_var.get())
    if path:
        app.tmp_var.set(str(path.resolve()))


def pick_courses_root(app: App) -> None:
    if busy(app):
        messagebox.showwarning("Smart Convert", "Stop the job before changing folders.")
        return
    path = browse_folder(
        app,
        "Select courses root (inbox/outbox/tmp inside)",
        app.inbox_var.get(),
    )
    if not path:
        return
    resolved = resolve_course_paths(courses_root=path)
    app.inbox_var.set(str(resolved.inbox))
    app.outbox_var.set(str(resolved.outbox))
    app.tmp_var.set(str(resolved.tmp))
    apply_paths(app)


def reset_paths_defaults(app: App) -> None:
    if busy(app):
        messagebox.showwarning("Smart Convert", "Stop the job before changing folders.")
        return
    defaults = resolve_course_paths()
    app.inbox_var.set(str(defaults.inbox))
    app.outbox_var.set(str(defaults.outbox))
    app.tmp_var.set(str(defaults.tmp))
    apply_paths(app)


def apply_paths(app: App) -> None:
    if busy(app):
        messagebox.showwarning("Smart Convert", "Stop the job before changing folders.")
        return
    inbox = app.inbox_var.get().strip()
    outbox = app.outbox_var.get().strip()
    tmp = app.tmp_var.get().strip()
    if not inbox or not outbox or not tmp:
        messagebox.showerror("Smart Convert", "inbox, outbox and tmp must all be set.")
        return
    new_paths = CoursePaths(
        inbox=Path(inbox).expanduser().resolve(),
        outbox=Path(outbox).expanduser().resolve(),
        tmp=Path(tmp).expanduser().resolve(),
    )
    try:
        new_paths.ensure()
    except OSError as exc:
        messagebox.showerror("Smart Convert", f"Cannot create folders: {exc}")
        return
    app.paths = new_paths
    app.inbox_var.set(str(new_paths.inbox))
    app.outbox_var.set(str(new_paths.outbox))
    app.tmp_var.set(str(new_paths.tmp))
    try:
        app._persist_settings()
    except OSError as exc:
        messagebox.showerror("Smart Convert", f"Cannot save settings: {exc}")
        return
    cleanup_conversion_temps(app.paths.tmp)
    app._app_log(f"Paths applied. inbox={app.paths.inbox}")
    app.refresh_courses()


def open_in_explorer(app: App, path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        messagebox.showerror("Smart Convert", str(exc))


def open_inbox(app: App) -> None:
    open_in_explorer(app, app.paths.inbox)


def open_outbox(app: App) -> None:
    open_in_explorer(app, app.paths.outbox)
