from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from smart_convert_nvenc.ffmpeg_runner import FFmpegCancelled
from smart_convert_nvenc.models import (
    ConvertSettings,
    EncodeProfile,
    MediaInfo,
    SampleResult,
    VideoCodec,
)
from smart_convert_nvenc.pipeline import (
    choose_winner,
    convert_one,
    convert_video,
    output_path_for,
    sample_seek_seconds,
)


def _sample(profile: EncodeProfile, size: int) -> SampleResult:
    return SampleResult(profile=profile, path="x", size_bytes=size, elapsed_sec=1.0)


def test_sample_seek_seconds(media_info: MediaInfo, settings: ConvertSettings) -> None:
    assert sample_seek_seconds(media_info, settings) == 25.0
    short = MediaInfo(
        path=media_info.path,
        size_bytes=100,
        duration_sec=10.0,
        video_codec="h264",
        width=1,
        height=1,
        has_audio=False,
    )
    assert sample_seek_seconds(short, settings) == 0.0


def test_choose_winner_av1_smaller(hevc_profile: EncodeProfile, av1_profile: EncodeProfile) -> None:
    report = choose_winner(
        hevc=_sample(hevc_profile, 1000),
        av1=_sample(av1_profile, 500),
        original_bytes=10_000,
        duration_sec=100.0,
        sample_seconds=10.0,
        min_savings=0.10,
        force_profile=None,
    )
    assert report.winner.codec is VideoCodec.AV1
    assert report.projected_full_bytes == 5000
    assert report.worth_encoding is True


def test_choose_winner_skip_low_savings(hevc_profile: EncodeProfile, av1_profile: EncodeProfile) -> None:
    report = choose_winner(
        hevc=_sample(hevc_profile, 900),
        av1=_sample(av1_profile, 950),
        original_bytes=10_000,
        duration_sec=100.0,
        sample_seconds=10.0,
        min_savings=0.10,
        force_profile=None,
    )
    assert report.worth_encoding is False


def test_choose_winner_force(hevc_profile: EncodeProfile) -> None:
    report = choose_winner(
        hevc=None,
        av1=None,
        original_bytes=10_000,
        duration_sec=100.0,
        sample_seconds=10.0,
        min_savings=0.10,
        force_profile=hevc_profile,
    )
    assert report.winner is hevc_profile
    assert report.worth_encoding is True


def test_output_path_for(tmp_path: Path, hevc_profile: EncodeProfile) -> None:
    path = tmp_path / "lesson.mp4"
    assert output_path_for(path, hevc_profile).name == "lesson_nvenc_hevc.mp4"


def test_convert_video_dry_run_force(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x" * 1000)
    info = MediaInfo(
        path=str(src),
        size_bytes=1000,
        duration_sec=50.0,
        video_codec="h264",
        width=640,
        height=360,
        has_audio=True,
    )
    settings = ConvertSettings(
        sample_seconds=settings.sample_seconds,
        min_savings=0.10,
        dry_run=True,
        force_codec=VideoCodec.HEVC,
        audio=settings.audio,
    )
    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        patch("smart_convert_nvenc.pipeline.probe_media", return_value=info),
    ):
        decision = convert_video(src, settings)
    assert decision.compressed is True
    assert decision.profile is not None
    assert decision.profile.codec is VideoCodec.HEVC


def test_convert_video_skip_projected(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x" * 10_000)
    info = MediaInfo(
        path=str(src),
        size_bytes=10_000,
        duration_sec=100.0,
        video_codec="h264",
        width=640,
        height=360,
        has_audio=False,
    )

    def _fake_encode(**kwargs: object) -> float:
        out = Path(str(kwargs["output_path"]))
        # sample_seconds=20 → scale=5; 1900*5=9500 >= 9000 threshold → skip full encode
        out.write_bytes(b"y" * 1900)
        return 0.1

    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        patch("smart_convert_nvenc.pipeline.probe_media", return_value=info),
        patch("smart_convert_nvenc.pipeline.encode_file", side_effect=_fake_encode),
    ):
        decision = convert_video(src, settings)
    assert decision.compressed is False


def test_convert_video_full_success(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x" * 10_000)
    info = MediaInfo(
        path=str(src),
        size_bytes=10_000,
        duration_sec=100.0,
        video_codec="h264",
        width=640,
        height=360,
        has_audio=False,
    )
    phases: list[str] = []

    def _fake_encode(**kwargs: object) -> float:
        out = Path(str(kwargs["output_path"]))
        # sample small, full even smaller
        if kwargs.get("for_sample"):
            out.write_bytes(b"y" * 50)
        else:
            out.write_bytes(b"z" * 2000)
        return 0.2

    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        patch("smart_convert_nvenc.pipeline.probe_media", return_value=info),
        patch("smart_convert_nvenc.pipeline.encode_file", side_effect=_fake_encode),
    ):
        decision = convert_video(
            src,
            settings,
            log=lambda m: None,
            on_phase_progress=lambda p, f: phases.append(p),
            on_ffmpeg_progress=lambda line: None,
        )
    assert decision.compressed is True
    assert decision.output.exists()
    assert "encode" in phases


def test_convert_video_reject_weak_full(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x" * 10_000)
    info = MediaInfo(
        path=str(src),
        size_bytes=10_000,
        duration_sec=100.0,
        video_codec="h264",
        width=640,
        height=360,
        has_audio=False,
    )

    def _fake_encode(**kwargs: object) -> float:
        out = Path(str(kwargs["output_path"]))
        if kwargs.get("for_sample"):
            out.write_bytes(b"y" * 50)
        else:
            out.write_bytes(b"z" * 9500)
        return 0.2

    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        patch("smart_convert_nvenc.pipeline.probe_media", return_value=info),
        patch("smart_convert_nvenc.pipeline.encode_file", side_effect=_fake_encode),
    ):
        decision = convert_video(src, settings)
    assert decision.compressed is False
    assert decision.output == src.resolve()


def test_convert_video_cancelled(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        pytest.raises(FFmpegCancelled),
    ):
        convert_video(src, settings, should_stop=lambda: True)


def test_convert_video_bad_duration(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x")
    info = MediaInfo(
        path=str(src),
        size_bytes=1,
        duration_sec=0.0,
        video_codec="h264",
        width=1,
        height=1,
        has_audio=False,
    )
    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        patch("smart_convert_nvenc.pipeline.probe_media", return_value=info),
        pytest.raises(RuntimeError, match="duration"),
    ):
        convert_video(src, settings)


def test_convert_video_missing_file(tmp_path: Path, settings: ConvertSettings) -> None:
    with (
        patch("smart_convert_nvenc.pipeline.require_nvenc"),
        pytest.raises(FileNotFoundError),
    ):
        convert_video(tmp_path / "nope.mp4", settings)


def test_convert_one_returns_none_when_skipped(tmp_path: Path, settings: ConvertSettings) -> None:
    src = tmp_path / "a.mp4"
    src.write_bytes(b"x" * 100)
    with patch(
        "smart_convert_nvenc.pipeline.convert_video",
        return_value=type(
            "D",
            (),
            {"compressed": False, "output": src},
        )(),
    ):
        assert convert_one(src, settings) is None
