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
from smart_convert_nvenc.models import (
    AudioMode,
    AudioSettings,
    EncoderBackend,
    EncodeProfile,
    VideoCodec,
)


@pytest.fixture
def hevc() -> EncodeProfile:
    return EncodeProfile(codec=VideoCodec.HEVC, cq=28, backend=EncoderBackend.GPU)


@pytest.fixture
def av1() -> EncodeProfile:
    return EncodeProfile(
        codec=VideoCodec.AV1,
        cq=32,
        container_ext=".mkv",
        backend=EncoderBackend.GPU,
    )


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
    # samples drop audio (video-only size race; avoids MPEG-TS/MKV mux failures)
    assert audio_args(AudioSettings(mode=AudioMode.AAC), for_sample=True) == ["-an"]
    assert audio_args(AudioSettings(mode=AudioMode.COPY), for_sample=True) == ["-an"]


def test_audio_args_copy_adds_adtstoasc_for_mpegts_aac() -> None:
    args = audio_args(
        AudioSettings(mode=AudioMode.COPY),
        for_sample=False,
        input_path=Path("lesson.ts"),
        output_path=Path("out.mkv"),
        audio_codec="aac",
    )
    assert args == ["-c:a", "copy", "-bsf:a", "aac_adtstoasc"]
    plain = audio_args(
        AudioSettings(mode=AudioMode.COPY),
        for_sample=False,
        input_path=Path("lesson.mp4"),
        output_path=Path("out.mp4"),
        audio_codec="aac",
    )
    assert plain == ["-c:a", "copy"]


def test_audio_args_copy_skips_adtstoasc_for_mp2_in_mpg() -> None:
    args = audio_args(
        AudioSettings(mode=AudioMode.COPY),
        for_sample=False,
        input_path=Path("lesson.mpg"),
        output_path=Path("out.mkv"),
        audio_codec="mp2",
    )
    assert args == ["-c:a", "copy"]
    no_codec = audio_args(
        AudioSettings(mode=AudioMode.COPY),
        for_sample=False,
        input_path=Path("lesson.mpg"),
        output_path=Path("out.mkv"),
        audio_codec=None,
    )
    assert no_codec == ["-c:a", "copy"]


def test_video_args_hevc_and_av1(hevc: EncodeProfile, av1: EncodeProfile) -> None:
    hevc_args = video_args(hevc)
    assert "hevc_nvenc" in hevc_args
    assert "-tag:v" in hevc_args
    assert "hvc1" in hevc_args
    assert "-multipass" not in hevc_args
    assert "-rc-lookahead" not in hevc_args
    av1_args = video_args(av1)
    assert "av1_nvenc" in av1_args
    assert "hvc1" not in av1_args


def test_video_args_nvenc_multipass_and_lookahead() -> None:
    profile = EncodeProfile(
        codec=VideoCodec.HEVC,
        cq=28,
        backend=EncoderBackend.GPU,
        multipass=True,
        rc_lookahead=20,
    )
    args = video_args(profile)
    assert args[args.index("-multipass") + 1] == "fullres"
    assert args[args.index("-rc-lookahead") + 1] == "20"


def test_video_args_cpu_ignores_multipass() -> None:
    profile = EncodeProfile(
        codec=VideoCodec.HEVC,
        cq=28,
        backend=EncoderBackend.CPU,
        multipass=True,
        rc_lookahead=32,
    )
    args = video_args(profile)
    assert "-multipass" not in args
    assert "-rc-lookahead" not in args
    assert "libx265" in args


def test_video_args_cpu_preset_extremes() -> None:
    slow = EncodeProfile(
        codec=VideoCodec.HEVC,
        cq=28,
        preset="p7",
        backend=EncoderBackend.CPU,
    )
    fast = EncodeProfile(
        codec=VideoCodec.AV1,
        cq=32,
        preset="p1",
        container_ext=".mkv",
        backend=EncoderBackend.CPU,
    )
    assert "slow" in video_args(slow)
    assert "10" in video_args(fast)


def test_build_encode_args_cpu_skips_hwaccel(tmp_path: Path) -> None:
    profile = EncodeProfile(
        codec=VideoCodec.HEVC,
        cq=28,
        backend=EncoderBackend.CPU,
    )
    args = build_encode_args(
        input_path=tmp_path / "in.mp4",
        output_path=tmp_path / "out.mp4",
        profile=profile,
        audio=AudioSettings(),
        hwaccel="auto",
    )
    assert "-hwaccel" not in args
    assert "libx265" in args


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
    assert "-an" in args
    assert "0:a:0?" not in args
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
