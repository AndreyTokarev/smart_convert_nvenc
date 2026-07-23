from __future__ import annotations

from smart_convert_nvenc.progress import ProgressUpdate, clamp01, parse_ffmpeg_time_seconds


def test_parse_ffmpeg_time_seconds() -> None:
    assert parse_ffmpeg_time_seconds("frame= 10 fps=0.0 time=00:01:30.50 bitrate=N/A") == 90.5
    assert parse_ffmpeg_time_seconds("time=01:00:00.00") == 3600.0
    assert parse_ffmpeg_time_seconds("no time here") is None


def test_clamp01() -> None:
    assert clamp01(-1.0) == 0.0
    assert clamp01(0.5) == 0.5
    assert clamp01(2.0) == 1.0


def test_progress_update_defaults() -> None:
    update = ProgressUpdate(
        course_name="A",
        video_index=1,
        videos_in_course=2,
        video_name="a.mp4",
        phase="encode",
        file_fraction=0.5,
    )
    assert update.ffmpeg_line == ""
