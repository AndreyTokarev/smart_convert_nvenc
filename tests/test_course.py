from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from smart_convert_nvenc.course import (
    _phase_to_file_fraction,
    convert_course,
    iter_non_videos,
    iter_videos,
    list_course_dirs,
    tree_size,
)
from smart_convert_nvenc.ffmpeg_runner import FFmpegCancelled
from smart_convert_nvenc.models import ConvertSettings, EncodeProfile, VideoCodec, VideoDecision
from smart_convert_nvenc.paths import CoursePaths


def _make_course(inbox: Path, name: str) -> Path:
    course = inbox / name
    (course / "mod").mkdir(parents=True)
    video = course / "mod" / "lesson.mp4"
    video.write_bytes(b"v" * 10_000)
    notes = course / "readme.txt"
    notes.write_bytes(b"notes")
    return course


def test_list_and_iter(course_layout: CoursePaths) -> None:
    a = _make_course(course_layout.inbox, "Alpha")
    _make_course(course_layout.inbox, "beta")
    (course_layout.inbox / ".hidden").mkdir()
    dirs = list_course_dirs(course_layout.inbox)
    assert [d.name for d in dirs] == ["Alpha", "beta"]
    videos = iter_videos(a)
    assert len(videos) == 1
    assert videos[0].name == "lesson.mp4"
    non = iter_non_videos(a)
    assert any(p.name == "readme.txt" for p in non)
    assert tree_size(a) == 10_000 + len(b"notes")


def test_iter_videos_sorted_by_size_desc(tmp_path: Path) -> None:
    course = tmp_path / "C"
    course.mkdir()
    small = course / "small.mp4"
    large = course / "large.mp4"
    mid = course / "mid.mp4"
    small.write_bytes(b"a" * 100)
    mid.write_bytes(b"b" * 500)
    large.write_bytes(b"c" * 2000)
    names = [p.name for p in iter_videos(course)]
    assert names == ["large.mp4", "mid.mp4", "small.mp4"]


def test_list_course_dirs_by_size(course_layout: CoursePaths) -> None:
    small = course_layout.inbox / "SmallCourse"
    large = course_layout.inbox / "LargeCourse"
    small.mkdir()
    large.mkdir()
    (small / "a.mp4").write_bytes(b"x" * 100)
    (large / "b.mp4").write_bytes(b"y" * 5000)
    by_name = list_course_dirs(course_layout.inbox)
    assert [d.name for d in by_name] == ["LargeCourse", "SmallCourse"]
    by_size = list_course_dirs(course_layout.inbox, by_size=True)
    assert [d.name for d in by_size] == ["LargeCourse", "SmallCourse"]
    (small / "extra.bin").write_bytes(b"z" * 20_000)
    by_size2 = list_course_dirs(course_layout.inbox, by_size=True)
    assert [d.name for d in by_size2] == ["SmallCourse", "LargeCourse"]


def test_phase_fraction_racing_and_locked() -> None:
    assert _phase_to_file_fraction("sample_hevc", 0.5, racing=True) == pytest.approx(0.05)
    assert _phase_to_file_fraction("sample_av1", 1.0, racing=True) == pytest.approx(0.20)
    assert _phase_to_file_fraction("encode", 0.5, racing=True) == pytest.approx(0.60)
    assert _phase_to_file_fraction("done", 1.0, racing=True) == 1.0
    assert _phase_to_file_fraction("encode", 0.5, racing=False) == 0.5
    assert _phase_to_file_fraction("sample_hevc", 1.0, racing=False) == 0.0
    assert _phase_to_file_fraction("other", 1.0, racing=True) == 0.0


def test_convert_course_dry_run(course_layout: CoursePaths, settings: ConvertSettings) -> None:
    course = _make_course(course_layout.inbox, "Demo")
    profile = EncodeProfile(codec=VideoCodec.HEVC, cq=28)

    def _fake_convert(video: Path, *args: object, **kwargs: object) -> VideoDecision:
        out = Path(str(kwargs["output_path"])).with_suffix(".mp4")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"c" * 2000)
        return VideoDecision(
            source=video,
            original_size=video.stat().st_size,
            compressed=True,
            output=out,
            profile=profile,
            projected_or_final_size=2000,
        )

    dry = ConvertSettings(
        sample_seconds=settings.sample_seconds,
        min_savings=0.10,
        dry_run=True,
        audio=settings.audio,
        force_codec=VideoCodec.HEVC,
    )
    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        patch("smart_convert_nvenc.course.convert_video", side_effect=_fake_convert),
    ):
        result = convert_course(course, course_layout, dry, log=lambda m: None)
    assert result.compressed_course is True
    assert course.exists()
    assert not (course_layout.tmp / "Demo").exists()


def test_convert_course_not_worth(course_layout: CoursePaths, settings: ConvertSettings) -> None:
    course = _make_course(course_layout.inbox, "TinySave")
    profile = EncodeProfile(codec=VideoCodec.HEVC, cq=28)

    def _fake_convert(video: Path, *args: object, **kwargs: object) -> VideoDecision:
        return VideoDecision(
            source=video,
            original_size=video.stat().st_size,
            compressed=False,
            output=video,
            profile=profile,
            projected_or_final_size=video.stat().st_size,
        )

    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        patch("smart_convert_nvenc.course.convert_video", side_effect=_fake_convert),
    ):
        result = convert_course(course, course_layout, settings)
    assert result.compressed_course is False
    assert result.outbox_path.exists()
    assert not course.exists()


def test_convert_course_assemble_compressed(
    course_layout: CoursePaths, settings: ConvertSettings
) -> None:
    course = _make_course(course_layout.inbox, "BigSave")
    profile = EncodeProfile(codec=VideoCodec.HEVC, cq=28)
    progress_events: list[str] = []

    def _fake_convert(video: Path, *args: object, **kwargs: object) -> VideoDecision:
        out = Path(str(kwargs["output_path"])).with_suffix(".mp4")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"c" * 1000)
        on_phase = kwargs.get("on_phase_progress")
        if on_phase:
            on_phase("encode", 0.5)
            on_phase("done", 1.0)
        return VideoDecision(
            source=video,
            original_size=video.stat().st_size,
            compressed=True,
            output=out,
            profile=profile,
            projected_or_final_size=1000,
        )

    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        patch("smart_convert_nvenc.course.convert_video", side_effect=_fake_convert),
    ):
        result = convert_course(
            course,
            course_layout,
            settings,
            on_progress=lambda u: progress_events.append(u.phase),
        )
    assert result.compressed_course is True
    assert result.videos_compressed == 1
    out = course_layout.outbox / "BigSave"
    assert out.exists()
    assert any(p.suffix == ".mp4" for p in out.rglob("*"))
    assert (out / "readme.txt").exists()
    assert not course.exists()
    assert "encode" in progress_events


def test_convert_course_no_videos_passthrough(
    course_layout: CoursePaths, settings: ConvertSettings
) -> None:
    course = course_layout.inbox / "PdfOnly"
    course.mkdir()
    (course / "doc.pdf").write_bytes(b"x" * 500)
    with patch("smart_convert_nvenc.course.require_nvenc"):
        result = convert_course(course, course_layout, settings)
    assert result.videos_total == 0
    assert result.compressed_course is False
    assert (course_layout.outbox / "PdfOnly" / "doc.pdf").exists()


def test_convert_course_no_videos_dry_run(
    course_layout: CoursePaths, settings: ConvertSettings
) -> None:
    course = course_layout.inbox / "PdfOnly"
    course.mkdir()
    (course / "doc.pdf").write_bytes(b"x" * 500)
    dry = ConvertSettings(
        sample_seconds=settings.sample_seconds,
        min_savings=0.10,
        dry_run=True,
        audio=settings.audio,
    )
    with patch("smart_convert_nvenc.course.require_nvenc"):
        result = convert_course(course, course_layout, dry)
    assert course.exists()
    assert result.videos_total == 0

    course = _make_course(course_layout.inbox, "Clash")
    (course_layout.outbox / "Clash").mkdir()
    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        pytest.raises(FileExistsError),
    ):
        convert_course(course, course_layout, settings)


def test_convert_course_must_be_inbox_child(
    course_layout: CoursePaths, settings: ConvertSettings, tmp_path: Path
) -> None:
    other = tmp_path / "elsewhere"
    other.mkdir()
    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        pytest.raises(ValueError, match="direct child"),
    ):
        convert_course(other, course_layout, settings)


def test_convert_course_stop(course_layout: CoursePaths, settings: ConvertSettings) -> None:
    course = _make_course(course_layout.inbox, "StopMe")
    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        pytest.raises(FFmpegCancelled),
    ):
        convert_course(course, course_layout, settings, should_stop=lambda: True)
    assert not (course_layout.tmp / "StopMe").exists()


def test_convert_course_cleans_on_error(
    course_layout: CoursePaths, settings: ConvertSettings
) -> None:
    course = _make_course(course_layout.inbox, "Boom")

    def _boom(*args: object, **kwargs: object) -> VideoDecision:
        raise RuntimeError("encode failed")

    with (
        patch("smart_convert_nvenc.course.require_nvenc"),
        patch("smart_convert_nvenc.course.convert_video", side_effect=_boom),
        pytest.raises(RuntimeError, match="encode failed"),
    ):
        convert_course(course, course_layout, settings)
    assert not (course_layout.tmp / "Boom").exists()
    assert course.exists()
