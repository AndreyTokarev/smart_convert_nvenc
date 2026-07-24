from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .paths import default_data_root, is_frozen

_EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def _tool_name(name: str) -> str:
    return f"{name}{_EXE_SUFFIX}"


def _candidate_bundle_roots() -> list[Path]:
    roots: list[Path] = []
    if is_frozen():
        roots.append(Path(sys.executable).resolve().parent)
    try:
        roots.append(default_data_root())
    except RuntimeError:
        pass
    roots.append(Path.cwd().resolve())
    # Deduplicate while preserving order
    seen: set[Path] = set()
    ordered: list[Path] = []
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        ordered.append(root)
    return ordered


def find_bundled_bin_dir() -> Path | None:
    """Return ``…/ffmpeg/bin`` if it contains ffmpeg + ffprobe next to the app."""
    for root in _candidate_bundle_roots():
        bin_dir = root / "ffmpeg" / "bin"
        ffmpeg = bin_dir / _tool_name("ffmpeg")
        ffprobe = bin_dir / _tool_name("ffprobe")
        if ffmpeg.is_file() and ffprobe.is_file():
            return bin_dir
    return None


def resolve_tool(name: str) -> tuple[str, str]:
    """Resolve ffmpeg or ffprobe.

    Returns ``(absolute_or_name, source)`` where source is
    ``env`` | ``bundled`` | ``path``.
    """
    if name not in {"ffmpeg", "ffprobe"}:
        raise ValueError(f"Unknown tool: {name}")

    env_dir = os.environ.get("SMART_CONVERT_FFMPEG_DIR")
    if env_dir:
        candidate = Path(env_dir) / _tool_name(name)
        if candidate.is_file():
            return str(candidate.resolve()), "env"
        # Also allow env pointing at …/ffmpeg/bin or …/bin
        alt = Path(env_dir) / "bin" / _tool_name(name)
        if alt.is_file():
            return str(alt.resolve()), "env"

    bundled = find_bundled_bin_dir()
    if bundled is not None:
        return str((bundled / _tool_name(name)).resolve()), "bundled"

    which = shutil.which(name)
    if which:
        return which, "path"

    raise FileNotFoundError(name)


def ffmpeg_executable() -> str:
    path, _source = resolve_tool("ffmpeg")
    return path


def ffprobe_executable() -> str:
    path, _source = resolve_tool("ffprobe")
    return path


def describe_tools() -> list[str]:
    """Human-readable lines for validate_environment / logs."""
    lines: list[str] = []
    for name in ("ffmpeg", "ffprobe"):
        try:
            path, source = resolve_tool(name)
            lines.append(f"{name}: {path} ({source})")
        except FileNotFoundError:
            lines.append(f"{name}: not found")
    return lines
