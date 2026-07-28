from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .ffmpeg_runner import FFmpegCancelled, StopCheck
from .ffmpeg_tools import ffmpeg_executable
from .probe import ToolError, require_tools
from .win_paths import with_fs_paths

_VMAF_SCORE_RE = re.compile(r"VMAF score:\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
_libvmaf_cached: bool | None = None


def has_libvmaf(*, force_refresh: bool = False) -> bool:
    global _libvmaf_cached
    if _libvmaf_cached is not None and not force_refresh:
        return _libvmaf_cached
    require_tools()
    result = subprocess.run(
        [ffmpeg_executable(), "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = (result.stdout or "") + (result.stderr or "")
    _libvmaf_cached = "libvmaf" in text
    return _libvmaf_cached


def parse_vmaf_score(text: str) -> float | None:
    match = _VMAF_SCORE_RE.search(text)
    if not match:
        return None
    return float(match.group(1))


def score_vmaf(
    *,
    reference: Path,
    distorted: Path,
    seek_seconds: float,
    sample_seconds: float,
    should_stop: StopCheck | None = None,
) -> float:
    if should_stop and should_stop():
        raise FFmpegCancelled("Stopped by user")
    if not has_libvmaf():
        raise ToolError("FFmpeg без фильтра libvmaf — VMAF недоступен в этой сборке.")

    cmd = [
        ffmpeg_executable(),
        "-hide_banner",
        "-y",
        "-i",
        str(distorted),
        "-ss",
        f"{seek_seconds:.3f}",
        "-t",
        f"{sample_seconds:.3f}",
        "-i",
        str(reference),
        "-filter_complex",
        (
            "[0:v]setpts=PTS-STARTPTS[dist];"
            "[1:v]setpts=PTS-STARTPTS[ref];"
            "[dist][ref]libvmaf=n_threads=2"
        ),
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(
        with_fs_paths(cmd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if should_stop and should_stop():
        raise FFmpegCancelled("Stopped by user")
    blob = (result.stdout or "") + (result.stderr or "")
    score = parse_vmaf_score(blob)
    if score is not None:
        return score
    if result.returncode != 0:
        raise ToolError(f"VMAF failed (ffmpeg exit {result.returncode}):\n{blob[-2000:]}")
    raise ToolError("VMAF finished but score line not found in ffmpeg output.")
