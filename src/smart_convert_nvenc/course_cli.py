from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .course import convert_course, list_course_dirs
from .models import AudioSettings, ConvertSettings, VideoCodec
from .paths import resolve_course_paths
from .probe import ToolError, validate_environment
from .temp_paths import cleanup_conversion_temps
from .windows_guard import WindowsSessionGuard


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smart-convert-course",
        description=(
            "Process course folders from courses/inbox via NVENC, "
            "then publish to courses/outbox (ADR-0001)."
        ),
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
    p.add_argument("--sample-sec", type=float, default=20.0)
    p.add_argument("--offset-ratio", type=float, default=0.25)
    p.add_argument("--min-savings", type=float, default=0.10, help="Per-video min savings")
    p.add_argument(
        "--min-course-savings",
        type=float,
        default=0.10,
        help="Whole-course min savings to keep compression",
    )
    p.add_argument("--cq-hevc", type=int, default=28)
    p.add_argument("--cq-av1", type=int, default=32)
    p.add_argument("--preset", default="p6")
    p.add_argument("--audio", default="copy")
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
        for line in validate_environment():
            _safe_print(f"env: {line}")
        removed = cleanup_conversion_temps(paths.tmp)
        if removed:
            _safe_print(f"Cleaned {len(removed)} leftover conversion temp(s)")

        audio = AudioSettings.parse(args.audio)
        force = VideoCodec(args.force_codec) if args.force_codec else None
        settings = ConvertSettings(
            sample_seconds=args.sample_sec,
            sample_offset_ratio=args.offset_ratio,
            min_savings=args.min_savings,
            hevc_cq=args.cq_hevc,
            av1_cq=args.cq_av1,
            preset=args.preset,
            audio=audio,
            dry_run=args.dry_run,
            force_codec=force,
            skip_same_codec=not args.reencode_same_codec,
        )

        if args.course:
            course_dir = paths.inbox / args.course
            if not course_dir.is_dir():
                raise FileNotFoundError(f"Course not found in inbox: {course_dir}")
            courses = [course_dir]
        else:
            courses = list_course_dirs(paths.inbox)
            if not courses:
                _safe_print(f"No course folders in {paths.inbox}")
                return 0

        guard = WindowsSessionGuard()
        guard.start()
        _safe_print("Windows guard ON (sleep blocked, pending reboot aborted while running)")
        try:
            for course_dir in courses:
                convert_course(
                    course_dir,
                    paths,
                    settings,
                    min_course_savings=args.min_course_savings,
                    race_once=not args.race_each,
                    log=_safe_print,
                )
        finally:
            guard.stop()
            _safe_print("Windows guard OFF")
        return 0
    except (ToolError, FileNotFoundError, FileExistsError, ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
