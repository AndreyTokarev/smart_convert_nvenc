from __future__ import annotations

from unittest.mock import patch

import pytest

from smart_convert_nvenc.vmaf import has_libvmaf, parse_vmaf_score, score_vmaf
from smart_convert_nvenc.ffmpeg_runner import FFmpegCancelled
from smart_convert_nvenc.probe import ToolError


def test_parse_vmaf_score() -> None:
    assert parse_vmaf_score("VMAF score: 93.456") == pytest.approx(93.456)
    assert parse_vmaf_score("noise") is None


def test_has_libvmaf_parses_filters() -> None:
    with (
        patch("smart_convert_nvenc.vmaf.require_tools"),
        patch("smart_convert_nvenc.vmaf.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.vmaf.subprocess.run") as run,
    ):
        run.return_value.stdout = " ... libvmaf  VMAF ...\n"
        run.return_value.stderr = ""
        assert has_libvmaf(force_refresh=True) is True
        run.return_value.stdout = "scale,overlay\n"
        assert has_libvmaf(force_refresh=True) is False


def test_score_vmaf_reads_output(tmp_path) -> None:
    ref = tmp_path / "ref.mp4"
    dist = tmp_path / "dist.mp4"
    ref.write_bytes(b"x")
    dist.write_bytes(b"y")
    with (
        patch("smart_convert_nvenc.vmaf.has_libvmaf", return_value=True),
        patch("smart_convert_nvenc.vmaf.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.vmaf.subprocess.run") as run,
    ):
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = "VMAF score: 91.25\n"
        assert score_vmaf(
            reference=ref,
            distorted=dist,
            seek_seconds=1.0,
            sample_seconds=2.0,
        ) == pytest.approx(91.25)


def test_score_vmaf_requires_libvmaf(tmp_path) -> None:
    ref = tmp_path / "ref.mp4"
    dist = tmp_path / "dist.mp4"
    ref.write_bytes(b"x")
    dist.write_bytes(b"y")
    with patch("smart_convert_nvenc.vmaf.has_libvmaf", return_value=False):
        with pytest.raises(ToolError, match="libvmaf"):
            score_vmaf(
                reference=ref,
                distorted=dist,
                seek_seconds=0,
                sample_seconds=1,
            )


def test_score_vmaf_cancelled_before_run(tmp_path) -> None:
    ref = tmp_path / "ref.mp4"
    dist = tmp_path / "dist.mp4"
    ref.write_bytes(b"x")
    dist.write_bytes(b"y")
    with patch("smart_convert_nvenc.vmaf.has_libvmaf", return_value=True):
        with pytest.raises(FFmpegCancelled):
            score_vmaf(
                reference=ref,
                distorted=dist,
                seek_seconds=0,
                sample_seconds=1,
                should_stop=lambda: True,
            )


def test_score_vmaf_missing_score_raises(tmp_path) -> None:
    ref = tmp_path / "ref.mp4"
    dist = tmp_path / "dist.mp4"
    ref.write_bytes(b"x")
    dist.write_bytes(b"y")
    with (
        patch("smart_convert_nvenc.vmaf.has_libvmaf", return_value=True),
        patch("smart_convert_nvenc.vmaf.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.vmaf.subprocess.run") as run,
    ):
        run.return_value.returncode = 1
        run.return_value.stdout = ""
        run.return_value.stderr = "encode fail"
        with pytest.raises(ToolError, match="VMAF failed"):
            score_vmaf(
                reference=ref,
                distorted=dist,
                seek_seconds=0,
                sample_seconds=1,
            )
        run.return_value.returncode = 0
        run.return_value.stderr = "no score here"
        with pytest.raises(ToolError, match="score line not found"):
            score_vmaf(
                reference=ref,
                distorted=dist,
                seek_seconds=0,
                sample_seconds=1,
            )
