from __future__ import annotations

import re
from dataclasses import dataclass


_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
_SPEED_RE = re.compile(r"speed=\s*([0-9]+(?:\.[0-9]+)?)x", re.IGNORECASE)


def parse_ffmpeg_time_seconds(line: str) -> float | None:
    match = _TIME_RE.search(line)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_ffmpeg_speed(line: str) -> float | None:
    match = _SPEED_RE.search(line)
    if not match:
        return None
    return float(match.group(1))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def trim_textbox_line_count(current_lines: int, max_lines: int) -> int:
    """How many leading lines to delete to keep a textbox within max_lines."""
    if max_lines <= 0 or current_lines <= max_lines:
        return 0
    return current_lines - max_lines


@dataclass(frozen=True)
class ProgressUpdate:
    """Progress for GUI / reporters."""

    course_name: str
    video_index: int  # 1-based within current course
    videos_in_course: int
    video_name: str
    phase: str
    file_fraction: float  # 0..1 for current video (all phases combined)
    ffmpeg_line: str = ""
    ffmpeg_speed: float | None = None
