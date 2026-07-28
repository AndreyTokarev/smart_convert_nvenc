from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .duplicates import format_report, scan_duplicates
from .paths import ensure_long_paths, resolve_course_paths


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smart-convert-duplicates",
        description=(
            "Find duplicate course folders (same name) and exact duplicate files "
            "(same size + SHA-256). Report only — never deletes."
        ),
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "roots",
        nargs="*",
        type=Path,
        help="Directories to scan (default: courses/inbox + courses/outbox)",
    )
    p.add_argument("--courses-root", type=Path, default=None)
    p.add_argument("--inbox", type=Path, default=None)
    p.add_argument("--outbox", type=Path, default=None)
    p.add_argument(
        "--min-size",
        type=int,
        default=1024 * 1024,
        help="Ignore files smaller than this many bytes (default: 1 MiB)",
    )
    p.add_argument(
        "--videos-only",
        action="store_true",
        help="Only compare video extensions for exact-file duplicates",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write Markdown report to this path (also printed to stdout)",
    )
    return p


def _default_roots(
    *,
    courses_root: Path | None,
    inbox: Path | None,
    outbox: Path | None,
) -> list[Path]:
    paths = resolve_course_paths(courses_root=courses_root, inbox=inbox, outbox=outbox)
    return [paths.inbox, paths.outbox]


def main(argv: list[str] | None = None) -> int:
    ensure_long_paths()
    args = build_parser().parse_args(argv)
    try:
        roots = list(args.roots) if args.roots else _default_roots(
            courses_root=args.courses_root,
            inbox=args.inbox,
            outbox=args.outbox,
        )
        missing = [r for r in roots if not r.is_dir()]
        if missing and args.roots:
            raise FileNotFoundError(
                "Not a directory: " + ", ".join(str(p) for p in missing)
            )
        roots = [r for r in roots if r.is_dir()]
        if not roots:
            print("No existing scan roots (create courses/inbox or pass a path).", file=sys.stderr)
            return 1

        report = scan_duplicates(
            roots,
            min_size=max(0, args.min_size),
            videos_only=args.videos_only,
        )
        text = format_report(report)
        print(text, end="")
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Wrote {args.output}", file=sys.stderr)
        return 0
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
