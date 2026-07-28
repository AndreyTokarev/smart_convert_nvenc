from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .course import convert_course, list_course_dirs
from .course_meta import load_course_meta
from .log_sink import tee_log
from .models import VideoCodec
from .paths import resolve_course_paths
from .probe import ToolError, validate_environment
from .profiles import get_profile, list_profile_names
from .session import SessionStats, default_session_report_path, write_session_report
from .temp_paths import cleanup_conversion_temps
from .windows_guard import WindowsSessionGuard


def build_parser() -> argparse.ArgumentParser:
    profiles = list_profile_names()
    p = argparse.ArgumentParser(
        prog="smart-convert-course",
        description=(
            "Process course folders from courses/inbox (NVENC or CPU), "
            "then publish to courses/outbox (ADR-0001)."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    p.add_argument(
        "course",
        nargs="?",
        default=None,
        help="Course folder name inside inbox (default: all courses)",
    )
    p.add_argument("--courses-root", type=Path, default=None)
    p.add_argument("--inbox", type=Path, default=None)
    p.add_argument("--outbox", type=Path, default=None)
    p.add_argument("--tmp", type=Path, default=None)
    p.add_argument(
        "--profile",
        default="default",
        choices=profiles,
        help="Named preset from profiles.toml (CLI flags override). Use 'course' for archive CQ/Opus.",
    )
    p.add_argument("--sample-sec", type=float, default=None)
    p.add_argument("--offset-ratio", type=float, default=None)
    p.add_argument(
        "--sample-fragments",
        type=int,
        default=None,
        help="Average N sample clips for race (default: from profile)",
    )
    p.add_argument("--min-savings", type=float, default=None, help="Per-video min savings")
    p.add_argument(
        "--min-course-savings",
        type=float,
        default=None,
        help="Whole-course min savings to keep compression (default: from profile)",
    )
    p.add_argument("--cq-hevc", type=int, default=None)
    p.add_argument("--cq-av1", type=int, default=None)
    p.add_argument("--preset", default=None)
    p.add_argument(
        "--encoder",
        choices=["gpu", "cpu", "auto"],
        default=None,
        help="gpu=NVENC only; cpu=libx265/libsvtav1; auto=NVENC if available else CPU",
    )
    p.add_argument(
        "--vmaf",
        choices=["off", "auto", "on"],
        default=None,
        help="Hybrid VMAF for sample race (default: from profile)",
    )
    p.add_argument("--vmaf-min", type=float, default=None)
    p.add_argument(
        "--nvenc-multipass",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="NVENC multipass fullres (off by default)",
    )
    p.add_argument(
        "--nvenc-lookahead",
        type=int,
        default=None,
        help="NVENC rc-lookahead (0=off)",
    )
    p.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Append app log lines to this file",
    )
    p.add_argument("--audio", default=None)
    p.add_argument("--force-codec", choices=["hevc", "av1"], default=None)
    p.add_argument(
        "--race-each",
        action="store_true",
        help="Race HEVC vs AV1 on every video (default: race once, reuse winner)",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--reencode-same-codec",
        action="store_true",
        help="Do not skip videos already in HEVC/AV1 (or the forced codec)",
    )
    p.add_argument(
        "--overwrite-outbox",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Replace existing outbox/<course> (default: yes). Use --no-overwrite-outbox to fail instead.",
    )
    p.add_argument(
        "--session-report",
        type=Path,
        nargs="?",
        const=Path("__AUTO__"),
        default=Path("__AUTO__"),
        help=(
            "Write Markdown session report (default: <courses>/session-report.md). "
            "Pass a path to override."
        ),
    )
    p.add_argument(
        "--no-session-report",
        action="store_true",
        help="Do not write session-report.md",
    )
    return p


def _safe_print(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(
            message.encode(encoding, errors="replace").decode(encoding, errors="replace"),
            flush=True,
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = resolve_course_paths(
            courses_root=args.courses_root,
            inbox=args.inbox,
            outbox=args.outbox,
            tmp=args.tmp,
        )
        paths.ensure()
        profile = get_profile(args.profile)
        settings = profile.to_convert_settings(
            sample_seconds=args.sample_sec,
            sample_offset_ratio=args.offset_ratio,
            sample_fragments=args.sample_fragments,
            min_savings=args.min_savings,
            hevc_cq=args.cq_hevc,
            av1_cq=args.cq_av1,
            preset=args.preset,
            audio=args.audio,
            encoder=args.encoder,
            vmaf=args.vmaf,
            vmaf_min=args.vmaf_min,
            nvenc_multipass=args.nvenc_multipass,
            nvenc_lookahead=args.nvenc_lookahead,
            dry_run=args.dry_run,
            force_codec=VideoCodec(args.force_codec) if args.force_codec else None,
            skip_same_codec=not args.reencode_same_codec,
        )
        min_course_savings = (
            profile.min_course_savings if args.min_course_savings is None else args.min_course_savings
        )
        log = tee_log(_safe_print, args.log_file)
        for line in validate_environment(settings.encoder):
            log(f"env: {line}")
        removed = cleanup_conversion_temps(paths.tmp)
        if removed:
            log(f"Cleaned {len(removed)} leftover conversion temp(s)")

        if args.course:
            course_dir = paths.inbox / args.course
            if not course_dir.is_dir():
                raise FileNotFoundError(f"Course not found in inbox: {course_dir}")
            courses = [course_dir]
        else:
            courses = list_course_dirs(paths.inbox, by_size=True)
            if not courses:
                log(f"No course folders in {paths.inbox}")
                return 0

        guard = WindowsSessionGuard()
        guard.start()
        log("Windows guard ON (sleep blocked, pending reboot aborted while running)")
        session = SessionStats()
        try:
            for course_dir in courses:
                result = convert_course(
                    course_dir,
                    paths,
                    settings,
                    min_course_savings=min_course_savings,
                    race_once=not args.race_each,
                    overwrite_outbox=bool(args.overwrite_outbox),
                    log=log,
                )
                meta = load_course_meta(course_dir)
                session.add_course(
                    result.name,
                    result.original_size,
                    result.final_size,
                    compressed=result.compressed_course,
                    videos_compressed=result.videos_compressed,
                    videos_total=result.videos_total,
                    outbox_path=str(result.outbox_path),
                    title=meta.title if meta and meta.title.strip() else None,
                    publishers=meta.publishers if meta else (),
                    authors=meta.authors if meta else (),
                    year=meta.year if meta else None,
                )
            if session.courses:
                log(session.summary_line())
                if not args.no_session_report:
                    report_arg = args.session_report
                    if report_arg is None or report_arg == Path("__AUTO__"):
                        report_path = default_session_report_path(inbox=paths.inbox)
                    else:
                        report_path = report_arg
                    written = write_session_report(session, report_path)
                    log(f"Session report: {written}")
        finally:
            guard.stop()
            log("Windows guard OFF")
        return 0
    except (ToolError, FileNotFoundError, FileExistsError, ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
