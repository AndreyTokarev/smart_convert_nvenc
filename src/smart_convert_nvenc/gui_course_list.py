from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk
import tkinter as tk

from .course import list_course_dirs, tree_size
from .course_meta import display_label, load_course_meta, tooltip_text
from .gui_theme import COLORS

if TYPE_CHECKING:
    from .gui import App


def course_list_label(course: Path) -> str:
    size_mib = tree_size(course) / (1024 * 1024)
    meta = load_course_meta(course)
    return f"{display_label(course.name, meta)}  ({size_mib:.0f} MiB)"


def refresh_courses(app: App) -> None:
    for child in app.course_list.winfo_children():
        child.destroy()
    app._course_vars.clear()
    courses = list_course_dirs(app.paths.inbox, by_size=True)
    app.course_count.configure(text=f"{len(courses)} found")
    if not courses:
        ctk.CTkLabel(
            app.course_list,
            text="Inbox is empty — drop course folders into the inbox path",
            font=app._font_ui,
            text_color=COLORS["muted"],
        ).pack(anchor="w", padx=8, pady=12)
        return
    for course in courses:
        var = tk.BooleanVar(value=False)
        size_mib = tree_size(course) / (1024 * 1024)
        meta = load_course_meta(course)
        row = ctk.CTkFrame(app.course_list, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=4)
        ctk.CTkCheckBox(
            row,
            text=f"{display_label(course.name, meta)}  ({size_mib:.0f} MiB)",
            variable=var,
            font=app._font_course,
            text_color=COLORS["text"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#ffffff",
        ).pack(anchor="w", fill="x")
        tip = tooltip_text(course.name, meta, size_mib=size_mib)
        detail_lines = tip.splitlines()[2:]  # skip folder + size (already in checkbox)
        if detail_lines:
            ctk.CTkLabel(
                row,
                text=" · ".join(detail_lines),
                anchor="w",
                font=app._font_ui,
                text_color=COLORS["muted"],
            ).pack(anchor="w", padx=(28, 0), pady=(0, 2))
        app._course_vars.append((var, course))
    app._app_log(f"Found {len(courses)} course(s) in inbox")


def select_all(app: App) -> None:
    for var, _ in app._course_vars:
        var.set(True)


def select_none(app: App) -> None:
    for var, _ in app._course_vars:
        var.set(False)


def selected_courses(app: App) -> list[Path]:
    return [path for var, path in app._course_vars if var.get()]
