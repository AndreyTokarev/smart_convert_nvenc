"""Thin entrypoints for PyInstaller one-file builds."""

from __future__ import annotations

from smart_convert_nvenc.course_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
