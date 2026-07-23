from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


ProgressCallback = Callable[[str], None]


def run_ffmpeg(
    args: list[str],
    *,
    on_progress: ProgressCallback | None = None,
) -> float:
    cmd = ["ffmpeg", "-hide_banner", "-y", *args]
    started = time.perf_counter()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if on_progress and "time=" in line:
            on_progress(line)
    code = process.wait()
    elapsed = time.perf_counter() - started
    if code != 0:
        raise FFmpegError(f"FFmpeg завершился с кодом {code}: {' '.join(cmd)}")
    return elapsed
