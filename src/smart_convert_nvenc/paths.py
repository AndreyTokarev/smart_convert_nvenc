from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Prefer extended paths before classic MAX_PATH (~260) bites ffmpeg/Win32.
_WIN_LONG_PATH_THRESHOLD = 240
_LONG_PATHS_WARNED = False


def is_frozen() -> bool:
    """True when running as a PyInstaller (or similar) bundled binary."""
    return bool(getattr(sys, "frozen", False))


def long_paths_enabled() -> bool | None:
    """Return Windows ``LongPathsEnabled`` policy, or ``None`` if unknown/non-Windows.

    On non-Windows returns ``True`` (no MAX_PATH policy to worry about).
    """
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
    """Set ``LongPathsEnabled=1`` in HKLM when possible (needs admin).

    Returns ``True`` if already enabled or the value was written successfully.
    A reboot is sometimes required for every Win32 app to pick it up; ``fs_path``
    still uses ``\\\\?\\`` for long paths regardless.
    """
    if sys.platform != "win32":
        return True
    current = long_paths_enabled()
    if current is True:
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


def ensure_long_paths(*, try_enable: bool = True, warn: bool = True) -> bool:
    """Ensure Windows long-path policy is on; optionally try to enable it.

    Returns whether long paths are enabled after the attempt.
    """
    global _LONG_PATHS_WARNED
    if sys.platform != "win32":
        return True
    if long_paths_enabled() is True:
        return True
    if try_enable and try_enable_long_paths():
        return True
    if warn and not _LONG_PATHS_WARNED:
        _LONG_PATHS_WARNED = True
        print(
            "WARNING: Windows LongPathsEnabled is not 1. Long course paths may fail.\n"
            "  Fix (admin PowerShell): "
            "New-ItemProperty -Path "
            "'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' "
            "-Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force\n"
            "  Then reboot. Frozen builds also need a longPathAware manifest "
            "(included in release packaging).",
            file=sys.stderr,
        )
    return False


def fs_path(path: Path | str) -> str:
    """String path for Win32 / ffmpeg; adds ``\\\\?\\`` when needed on Windows."""
    raw = Path(path)
    if sys.platform != "win32":
        return os.fspath(raw)

    try:
        if raw.exists():
            text = os.fspath(raw.resolve())
        elif raw.is_absolute():
            parent = raw.parent
            text = (
                os.fspath(parent.resolve() / raw.name)
                if parent.exists()
                else os.fspath(raw)
            )
        else:
            text = os.fspath(raw.resolve(strict=False))
    except OSError:
        text = os.fspath(raw)

    if text.startswith("\\\\?\\"):
        return text

    enabled = long_paths_enabled()
    if len(text) < _WIN_LONG_PATH_THRESHOLD and enabled is True:
        return text

    if text.startswith("\\\\"):
        # UNC \\server\share\... → \\?\UNC\server\share\...
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def find_project_root(start: Path | None = None) -> Path:
    """Resolve repo root (directory containing pyproject.toml)."""
    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    candidates.append(Path(__file__).resolve())
    candidates.append(Path.cwd().resolve())

    seen: set[Path] = set()
    for base in candidates:
        for path in [base, *base.parents]:
            if path in seen:
                continue
            seen.add(path)
            if (path / "pyproject.toml").is_file():
                return path
    raise RuntimeError("Не найден корень проекта (pyproject.toml).")


def default_data_root() -> Path:
    """Directory used for default ``courses/`` layout.

    - Dev / source install: repo root (``pyproject.toml``).
    - Frozen exe: directory containing the binary (portable zip layout).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return find_project_root()


@dataclass(frozen=True)
class CoursePaths:
    inbox: Path
    outbox: Path
    tmp: Path

    def ensure(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)


def resolve_course_paths(
    *,
    courses_root: Path | None = None,
    inbox: Path | None = None,
    outbox: Path | None = None,
    tmp: Path | None = None,
    project_root: Path | None = None,
) -> CoursePaths:
    env_root = os.environ.get("SMART_CONVERT_COURSES_ROOT")
    env_inbox = os.environ.get("SMART_CONVERT_INBOX")
    env_outbox = os.environ.get("SMART_CONVERT_OUTBOX")
    env_tmp = os.environ.get("SMART_CONVERT_TMP")

    resolved_inbox = inbox or (Path(env_inbox) if env_inbox else None)
    resolved_outbox = outbox or (Path(env_outbox) if env_outbox else None)
    resolved_tmp = tmp or (Path(env_tmp) if env_tmp else None)

    if resolved_inbox is None or resolved_outbox is None or resolved_tmp is None:
        if courses_root is not None:
            base = courses_root
        elif env_root:
            base = Path(env_root)
        else:
            root = project_root or default_data_root()
            base = root / "courses"
        if resolved_inbox is None:
            resolved_inbox = base / "inbox"
        if resolved_outbox is None:
            resolved_outbox = base / "outbox"
        if resolved_tmp is None:
            resolved_tmp = base / "tmp"

    return CoursePaths(
        inbox=resolved_inbox.resolve(),
        outbox=resolved_outbox.resolve(),
        tmp=resolved_tmp.resolve(),
    )
