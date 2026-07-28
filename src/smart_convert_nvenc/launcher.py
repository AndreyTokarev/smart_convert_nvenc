from __future__ import annotations

import sys

from .win_paths import long_paths_enabled, try_enable_long_paths


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


def _cmd_enable_long_paths() -> int:
    if long_paths_enabled() is True:
        print("LongPathsEnabled is already 1.")
        return 0
    if try_enable_long_paths():
        print(
            "LongPathsEnabled set to 1. Reboot (or sign out) so all Win32 apps pick it up.\n"
            "FFmpeg I/O already uses \\\\?\\ paths without a reboot."
        )
        return 0
    print(
        "Could not set LongPathsEnabled (need Administrator).\n"
        "Run an elevated PowerShell:\n"
        "  New-ItemProperty -Path "
        "'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' "
        "-Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    """Single entry for release binary and ``python -m smart_convert_nvenc``.

    Modes:
    - no args / ``gui`` → desktop GUI
    - ``course`` … → course inbox/outbox CLI
    - ``enable-long-paths`` → admin helper for OS policy (not used on normal runs)
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

    if args[0] in {"duplicates", "dupes"}:
        from .duplicates_cli import main as duplicates_main

        return int(duplicates_main(args[1:]))

    if args[0] in {"enable-long-paths"}:
        return _cmd_enable_long_paths()

    if args[0] in {"-h", "--help", "help"}:
        print(
            "smart-convert — compress course videos (NVENC / CPU)\n\n"
            "Usage:\n"
            "  smart-convert                 Start GUI\n"
            "  smart-convert gui             Start GUI\n"
            "  smart-convert course [opts]   Process courses/inbox\n"
            "  smart-convert duplicates …   Duplicate report (no delete)\n"
            "  smart-convert enable-long-paths\n"
            "      Set Windows LongPathsEnabled=1 (Administrator)\n"
            "  smart-convert <video> [opts]  Convert one file\n"
            "  smart-convert --version\n"
        )
        return 0

    from .cli import main as cli_main

    return int(cli_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
