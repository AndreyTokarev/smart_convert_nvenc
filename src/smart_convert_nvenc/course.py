from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_runner import FFmpegCancelled, StopCheck
from .models import ConvertSettings, EncodeProfile, VIDEO_EXTENSIONS, VideoDecision
from .paths import CoursePaths
from .pipeline import convert_video
from .probe import require_nvenc
from .progress import ProgressUpdate, clamp01
from .temp_paths import cleanup_conversion_temps


LogFn = Callable[[str], None]
ProgressFn = Callable[[ProgressUpdate], None]


def _log(log: LogFn | None, message: str) -> None:
    if log:
        log(message)


def _format_mb(size: int) -> str:
    return f"{size / (1024 * 1024):.2f} MiB"


def tree_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def list_course_dirs(inbox: Path) -> list[Path]:
    return sorted(
        (p for p in inbox.iterdir() if p.is_dir() and not p.name.startswith(".")),
        key=lambda p: p.name.lower(),
    )


def iter_videos(course_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(course_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]


def iter_non_videos(course_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(course_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() not in VIDEO_EXTENSIONS
    ]


@dataclass
class CourseResult:
    name: str
    original_size: int
    final_size: int
    compressed_course: bool
    outbox_path: Path
    videos_compressed: int
    videos_total: int


def _safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _move_path(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))


def _phase_to_file_fraction(phase: str, local: float, *, racing: bool) -> float:
    local = clamp01(local)
    if not racing:
        if phase in {"encode", "done"}:
            return local
        return 0.0
    if phase == "sample_hevc":
        return 0.10 * local
    if phase == "sample_av1":
        return 0.10 + 0.10 * local
    if phase == "encode":
        return 0.20 + 0.80 * local
    if phase == "done":
        return 1.0
    return 0.0


def convert_course(
    course_dir: Path,
    paths: CoursePaths,
    settings: ConvertSettings,
    *,
    min_course_savings: float = 0.10,
    race_once: bool = True,
    log: LogFn | None = None,
    on_ffmpeg_progress: LogFn | None = None,
    on_progress: ProgressFn | None = None,
    should_stop: StopCheck | None = None,
) -> CourseResult:
    require_nvenc()
    course_dir = course_dir.resolve()
    if not course_dir.is_dir():
        raise FileNotFoundError(course_dir)
    if course_dir.parent.resolve() != paths.inbox.resolve():
        raise ValueError(f"Course must be a direct child of inbox: {paths.inbox}")

    name = course_dir.name
    out_course = paths.outbox / name
    tmp_course = paths.tmp / name

    if out_course.exists():
        raise FileExistsError(
            f"Outbox already has '{name}'. Remove or rename it before retrying."
        )

    removed = cleanup_conversion_temps(paths.tmp)
    if removed:
        _log(log, f"Cleaned {len(removed)} leftover conversion temp(s) under tmp")

    original_size = tree_size(course_dir)
    videos = iter_videos(course_dir)
    non_videos = iter_non_videos(course_dir)

    _log(log, "=" * 60)
    _log(log, f"Course: {name}")
    _log(
        log,
        f"Size: {_format_mb(original_size)}, videos: {len(videos)}, other files: {len(non_videos)}",
    )

    if not videos:
        _log(log, "No video files — pass-through inbox -> outbox (nothing to encode)")
        if settings.dry_run:
            return CourseResult(
                name=name,
                original_size=original_size,
                final_size=original_size,
                compressed_course=False,
                outbox_path=out_course,
                videos_compressed=0,
                videos_total=0,
            )
        _move_path(course_dir, out_course)
        return CourseResult(
            name=name,
            original_size=original_size,
            final_size=original_size,
            compressed_course=False,
            outbox_path=out_course,
            videos_compressed=0,
            videos_total=0,
        )

    if tmp_course.exists():
        _log(log, f"Cleaning leftover tmp: {tmp_course}")
        _safe_rmtree(tmp_course)
    tmp_course.mkdir(parents=True, exist_ok=True)

    decisions: list[VideoDecision] = []
    locked_profile: EncodeProfile | None = None

    try:
        for index, video in enumerate(videos, start=1):
            if should_stop and should_stop():
                raise FFmpegCancelled("Stopped by user")
            rel = video.relative_to(course_dir)
            _log(log, f"[{index}/{len(videos)}] {rel}")

            out_path = tmp_course / rel
            racing = locked_profile is None and settings.force_codec is None

            def _on_phase(phase: str, local: float, *, idx=index, vid=video) -> None:
                if not on_progress:
                    return
                on_progress(
                    ProgressUpdate(
                        course_name=name,
                        video_index=idx,
                        videos_in_course=len(videos),
                        video_name=vid.name,
                        phase=phase,
                        file_fraction=_phase_to_file_fraction(phase, local, racing=racing),
                    )
                )

            decision = convert_video(
                video,
                settings,
                output_path=out_path,
                force_profile=locked_profile,
                log=log,
                on_ffmpeg_progress=on_ffmpeg_progress,
                on_phase_progress=_on_phase,
                should_stop=should_stop,
            )
            decisions.append(decision)
            if on_progress:
                on_progress(
                    ProgressUpdate(
                        course_name=name,
                        video_index=index,
                        videos_in_course=len(videos),
                        video_name=video.name,
                        phase="done",
                        file_fraction=1.0,
                    )
                )

            if (
                decision.compressed
                and decision.profile is not None
                and race_once
                and locked_profile is None
            ):
                locked_profile = decision.profile
                _log(
                    log,
                    f"  locking codec for rest of course: {locked_profile.codec.value.upper()}",
                )

        non_video_size = sum(p.stat().st_size for p in non_videos)
        candidate_size = sum(d.projected_or_final_size for d in decisions) + non_video_size
        savings = 1.0 - (candidate_size / original_size) if original_size else 0.0
        worth = candidate_size < original_size * (1.0 - min_course_savings)
        videos_compressed = sum(1 for d in decisions if d.compressed)

        _log(log, "-" * 60)
        _log(
            log,
            f"Course candidate: {_format_mb(candidate_size)} "
            f"(original {_format_mb(original_size)}, {savings * 100:.1f}%)",
        )
        _log(log, f"Videos compressed: {videos_compressed}/{len(videos)}")

        if settings.dry_run:
            _log(log, "Dry-run: no moves performed. Cleaning tmp encodes.")
            _safe_rmtree(tmp_course)
            return CourseResult(
                name=name,
                original_size=original_size,
                final_size=candidate_size if worth else original_size,
                compressed_course=worth,
                outbox_path=out_course,
                videos_compressed=videos_compressed,
                videos_total=len(videos),
            )

        if not worth:
            _log(log, "Course not worth compressing -> move original inbox -> outbox")
            _safe_rmtree(tmp_course)
            _move_path(course_dir, out_course)
            return CourseResult(
                name=name,
                original_size=original_size,
                final_size=original_size,
                compressed_course=False,
                outbox_path=out_course,
                videos_compressed=0,
                videos_total=len(videos),
            )

        _log(log, "Assembling compressed course into outbox...")
        out_course.mkdir(parents=True, exist_ok=True)

        for src in non_videos:
            rel = src.relative_to(course_dir)
            _move_path(src, out_course / rel)

        for decision in decisions:
            rel = decision.source.relative_to(course_dir)
            if decision.compressed:
                dest_rel = rel.with_name(Path(decision.output).name)
                _move_path(Path(decision.output), out_course / dest_rel)
                if decision.source.exists():
                    decision.source.unlink()
            else:
                _move_path(decision.source, out_course / rel)

        if course_dir.exists():
            for path in sorted(course_dir.rglob("*"), reverse=True):
                if path.is_dir():
                    try:
                        path.rmdir()
                    except OSError:
                        pass
            try:
                course_dir.rmdir()
            except OSError:
                for leftover in course_dir.rglob("*"):
                    if leftover.is_file():
                        _move_path(leftover, out_course / leftover.relative_to(course_dir))
                _safe_rmtree(course_dir)

        _safe_rmtree(tmp_course)
        final_size = tree_size(out_course)
        _log(
            log,
            f"DONE: {_format_mb(final_size)} "
            f"(saved {_format_mb(original_size - final_size)}, "
            f"{(1 - final_size / original_size) * 100:.1f}%)",
        )
        _log(log, f"Outbox: {out_course}")
        return CourseResult(
            name=name,
            original_size=original_size,
            final_size=final_size,
            compressed_course=True,
            outbox_path=out_course,
            videos_compressed=videos_compressed,
            videos_total=len(videos),
        )
    except Exception:
        _safe_rmtree(tmp_course)
        if out_course.exists():
            _safe_rmtree(out_course)
        raise
