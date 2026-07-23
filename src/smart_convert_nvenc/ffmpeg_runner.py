from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections.abc import Callable


class FFmpegError(RuntimeError):
    pass


class FFmpegCancelled(RuntimeError):
    pass


ProgressCallback = Callable[[str], None]
StopCheck = Callable[[], bool]

_active_processes: set[subprocess.Popen[str]] = set()
_active_lock = threading.Lock()


def _register(process: subprocess.Popen[str]) -> None:
    with _active_lock:
        _active_processes.add(process)


def _unregister(process: subprocess.Popen[str]) -> None:
    with _active_lock:
        _active_processes.discard(process)


def terminate_process(process: subprocess.Popen[str]) -> bool:
    if process.poll() is not None:
        return False
    try:
        if sys.platform == "win32" and process.pid:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
            )
        else:
            process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return True
    except OSError:
        return False


def kill_active_subprocesses() -> int:
    with _active_lock:
        processes = list(_active_processes)
    killed = 0
    for process in processes:
        if terminate_process(process):
            killed += 1
        _unregister(process)
    return killed


def run_ffmpeg(
    args: list[str],
    *,
    on_progress: ProgressCallback | None = None,
    should_stop: StopCheck | None = None,
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
    _register(process)
    cancelled = False
    try:
        assert process.stdout is not None
        for line in process.stdout:
            if should_stop and should_stop():
                cancelled = True
                terminate_process(process)
                break
            line = line.rstrip()
            if on_progress and "time=" in line:
                on_progress(line)
        code = process.wait()
    finally:
        _unregister(process)

    elapsed = time.perf_counter() - started
    if cancelled or (should_stop and should_stop()):
        raise FFmpegCancelled("FFmpeg cancelled by user")
    if code != 0:
        raise FFmpegError(f"FFmpeg exited with code {code}: {' '.join(cmd)}")
    return elapsed
