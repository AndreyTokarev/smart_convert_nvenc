# Windows path helpers for external tools (ffmpeg/ffprobe).

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

_LONG_PATHS_WARNED = False


def long_paths_enabled() -> bool | None:
    """Windows ``LongPathsEnabled`` policy. Non-Windows → ``True``. Unreadable → ``None``."""
    if sys.platform != "win32":
        return True
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
            return int(value) == 1
    except OSError:
        return None


def try_enable_long_paths() -> bool:
    """Explicit admin helper: set ``LongPathsEnabled=1``. Not called on normal startup."""
    if sys.platform != "win32":
        return True
    if long_paths_enabled() is True:
        return True
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "LongPathsEnabled", 0, winreg.REG_DWORD, 1)
        return long_paths_enabled() is True
    except OSError:
        return False


def warn_if_long_paths_disabled() -> None:
    """Print a one-shot stderr hint when the OS policy is off (no registry writes)."""
    global _LONG_PATHS_WARNED
    if sys.platform != "win32" or _LONG_PATHS_WARNED:
        return
    if long_paths_enabled() is True:
        return
    _LONG_PATHS_WARNED = True
    print(
        "WARNING: Windows LongPathsEnabled is not 1. Long course paths may fail "
        "for Python file ops (Explorer, shutil). FFmpeg I/O uses \\\\?\\ anyway.\n"
        "  Fix (admin): smart-convert enable-long-paths\n"
        "  Or: New-ItemProperty -Path "
        "'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' "
        "-Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force\n"
        "  Then reboot. Frozen builds include a longPathAware manifest.",
        file=sys.stderr,
    )


def fs_path(path: Path | str) -> str:
    """Absolute path string for Win32 / ffmpeg; always ``\\\\?\\``-prefixed on Windows."""
    text = str(Path(path).resolve(strict=False))
    if sys.platform != "win32" or text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text[2:]
    return "\\\\?\\" + text


def _looks_like_filesystem_arg(arg: str) -> bool:
    if not arg or arg.startswith("-"):
        return False
    if len(arg) >= 2 and arg[1] == ":":
        return True
    if arg.startswith("\\\\"):
        return True
    if "/" in arg or "\\" in arg:
        return True
    # Relative bare filenames passed as ffmpeg I/O (e.g. out.mp4)
    return bool(Path(arg).suffix)


def with_fs_paths(args: Sequence[str]) -> list[str]:
    """Apply ``fs_path`` to filesystem-looking argv entries (tool boundary)."""
    warn_if_long_paths_disabled()
    if sys.platform != "win32":
        return list(args)
    return [fs_path(a) if _looks_like_filesystem_arg(a) else a for a in args]


def prepare_tool_cmd(executable: str, args: Iterable[str]) -> list[str]:
    """Build ``[executable, …]`` with Windows extended paths on file args."""
    return [executable, *with_fs_paths(list(args))]
