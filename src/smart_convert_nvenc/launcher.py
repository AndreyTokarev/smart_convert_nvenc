from __future__ import annotations

import sys


def _hide_console_windows() -> None:
    """Hide the console window when a frozen GUI starts (console=True build)."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except OSError:
        return


def main(argv: list[str] | None = None) -> int:
    """Single entry for release binary and ``python -m smart_convert_nvenc``.

    Modes:
    - no args / ``gui`` → desktop GUI
    - ``course`` … → course inbox/outbox CLI
    - otherwise → single-file CLI (same argv as ``smart-convert``)
    """
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in {"gui", "--gui"}:
        _hide_console_windows()
        from .gui import main as gui_main

        return int(gui_main())

    if args[0] in {"course", "courses"}:
        from .course_cli import main as course_main

        return int(course_main(args[1:]))

    if args[0] in {"-h", "--help", "help"}:
        print(
            "smart-convert — compress course videos (NVENC / CPU)\n\n"
            "Usage:\n"
            "  smart-convert                 Start GUI\n"
            "  smart-convert gui             Start GUI\n"
            "  smart-convert course [opts]   Process courses/inbox\n"
            "  smart-convert <video> [opts]  Convert one file\n"
            "  smart-convert --version\n"
        )
        return 0

    from .cli import main as cli_main

    return int(cli_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
