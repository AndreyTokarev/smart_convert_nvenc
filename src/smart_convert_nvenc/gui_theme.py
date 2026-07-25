from __future__ import annotations

import customtkinter as ctk

COLORS = {
    "bg": "#1a1d21",
    "panel": "#23282e",
    "panel2": "#2a3038",
    "border": "#3a424c",
    "text": "#e8eaed",
    "muted": "#9aa3ad",
    "accent": "#3d8bfd",
    "accent_hover": "#2f74d8",
    "danger": "#c23b3b",
    "danger_hover": "#a32f2f",
    "ok": "#3fa66b",
}

APP_LOG_MAX_LINES = 2000
FF_LOG_MAX_LINES = 1000


def configure_appearance() -> None:
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
