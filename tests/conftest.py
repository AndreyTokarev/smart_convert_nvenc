from __future__ import annotations

from pathlib import Path

import pytest

from smart_convert_nvenc.models import (
    AudioSettings,
    ConvertSettings,
    EncodeProfile,
    MediaInfo,
    VideoCodec,
    VmafMode,
)
from smart_convert_nvenc.paths import CoursePaths


@pytest.fixture
def hevc_profile() -> EncodeProfile:
    return EncodeProfile(codec=VideoCodec.HEVC, cq=28, preset="p6", container_ext=".mp4")


@pytest.fixture
def av1_profile() -> EncodeProfile:
    return EncodeProfile(codec=VideoCodec.AV1, cq=32, preset="p6", container_ext=".mkv")


@pytest.fixture
def settings() -> ConvertSettings:
    return ConvertSettings(
        sample_seconds=20.0,
        sample_offset_ratio=0.25,
        min_savings=0.10,
        audio=AudioSettings.parse("copy"),
        # Unit tests must not call real ffmpeg for VMAF detect (CI has no ffmpeg).
        vmaf=VmafMode.OFF,
    )


@pytest.fixture
def media_info(tmp_path: Path) -> MediaInfo:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"x" * 1_000_000)
    return MediaInfo(
        path=str(path),
        size_bytes=1_000_000,
        duration_sec=100.0,
        video_codec="h264",
        width=1920,
        height=1080,
        has_audio=True,
    )


@pytest.fixture
def course_layout(tmp_path: Path) -> CoursePaths:
    root = tmp_path / "courses"
    paths = CoursePaths(
        inbox=root / "inbox",
        outbox=root / "outbox",
        tmp=root / "tmp",
    )
    paths.ensure()
    return paths
