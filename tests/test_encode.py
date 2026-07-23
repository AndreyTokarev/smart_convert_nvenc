from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_convert_nvenc.encode import (
    audio_args,
    build_encode_args,
    encode_file,
    video_args,
)
from smart_convert_nvenc.ffmpeg_runner import FFmpegCancelled, FFmpegError
from smart_convert_nvenc.models import AudioMode, AudioSettings, EncodeProfile, VideoCodec


@pytest.fixture
def hevc() -> EncodeProfile:
    return EncodeProfile(codec=VideoCodec.HEVC, cq=28)


@pytest.fixture
def av1() -> EncodeProfile:
    return EncodeProfile(codec=VideoCodec.AV1, cq=32, container_ext=".mkv")


def test_audio_args_modes() -> None:
    assert audio_args(AudioSettings(mode=AudioMode.COPY), for_sample=False) == ["-c:a", "copy"]
    assert audio_args(AudioSettings(mode=AudioMode.AAC, bitrate_k=96), for_sample=False) == [
        "-c:a",
        "aac",
        "-b:a",
        "96k",
    ]
    assert audio_args(AudioSettings(mode=AudioMode.OPUS, bitrate_k=64), for_sample=False) == [
        "-c:a",
        "libopus",
        "-b:a",
        "64k",
    ]
    # samples always copy
    assert audio_args(AudioSettings(mode=AudioMode.AAC), for_sample=True) == ["-c:a", "copy"]


def test_video_args_hevc_and_av1(hevc: EncodeProfile, av1: EncodeProfile) -> None:
    hevc_args = video_args(hevc)
    assert "hevc_nvenc" in hevc_args
    assert "-tag:v" in hevc_args
    assert "hvc1" in hevc_args
    av1_args = video_args(av1)
    assert "av1_nvenc" in av1_args
    assert "hvc1" not in av1_args


def test_build_encode_args_with_seek_and_sample(tmp_path: Path, hevc: EncodeProfile) -> None:
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    args = build_encode_args(
        input_path=inp,
        output_path=out,
        profile=hevc,
        audio=AudioSettings(),
        sample_seconds=10.0,
        seek_seconds=5.0,
        for_sample=True,
        hwaccel="auto",
    )
    assert args[:2] == ["-hwaccel", "auto"]
    assert "-ss" in args and "5.000" in args
    assert "-t" in args and "10.000" in args
    assert str(inp) in args
    assert str(out) in args


def test_build_encode_args_without_hwaccel(tmp_path: Path, hevc: EncodeProfile) -> None:
    args = build_encode_args(
        input_path=tmp_path / "in.mp4",
        output_path=tmp_path / "out.mp4",
        profile=hevc,
        audio=AudioSettings(),
        hwaccel=None,
    )
    assert "-hwaccel" not in args


def test_encode_file_promotes_temp(tmp_path: Path, hevc: EncodeProfile) -> None:
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"src")

    def _fake_run(args: list[str], **kwargs: object) -> float:
        # last arg is output temp path
        Path(args[-1]).write_bytes(b"encoded-data")
        return 1.5

    with patch("smart_convert_nvenc.encode.run_ffmpeg", side_effect=_fake_run):
        elapsed = encode_file(
            input_path=inp,
            output_path=out,
            profile=hevc,
            audio=AudioSettings(),
        )
    assert elapsed == 1.5
    assert out.read_bytes() == b"encoded-data"


def test_encode_file_retries_without_hwaccel(tmp_path: Path, hevc: EncodeProfile) -> None:
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"src")
    calls: list[list[str]] = []

    def _fake_run(args: list[str], **kwargs: object) -> float:
        calls.append(args)
        if "-hwaccel" in args:
            raise FFmpegError("hwaccel failed")
        Path(args[-1]).write_bytes(b"ok")
        return 2.0

    with patch("smart_convert_nvenc.encode.run_ffmpeg", side_effect=_fake_run):
        encode_file(
            input_path=inp,
            output_path=out,
            profile=hevc,
            audio=AudioSettings(),
        )
    assert len(calls) == 2
    assert "-hwaccel" in calls[0]
    assert "-hwaccel" not in calls[1]
    assert out.exists()


def test_encode_file_cancel_cleans_temp(tmp_path: Path, hevc: EncodeProfile) -> None:
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"src")

    def _fake_run(args: list[str], **kwargs: object) -> float:
        Path(args[-1]).write_bytes(b"partial")
        raise FFmpegCancelled("stop")

    with patch("smart_convert_nvenc.encode.run_ffmpeg", side_effect=_fake_run):
        with pytest.raises(FFmpegCancelled):
            encode_file(
                input_path=inp,
                output_path=out,
                profile=hevc,
                audio=AudioSettings(),
            )
    assert not out.exists()
    leftovers = list(tmp_path.glob("*.conv.*"))
    assert leftovers == []


def test_encode_file_no_retry(tmp_path: Path, hevc: EncodeProfile) -> None:
    inp = tmp_path / "in.mp4"
    out = tmp_path / "out.mp4"
    inp.write_bytes(b"src")

    with patch(
        "smart_convert_nvenc.encode.run_ffmpeg",
        side_effect=FFmpegError("boom"),
    ):
        with pytest.raises(FFmpegError):
            encode_file(
                input_path=inp,
                output_path=out,
                profile=hevc,
                audio=AudioSettings(),
                retry_without_hwaccel=False,
            )
