from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .log_sink import tee_log
from .models import VideoCodec
from .paths import ensure_long_paths
from .pipeline import convert_one
from .probe import ToolError, validate_environment
from .profiles import get_profile, list_profile_names


def build_parser() -> argparse.ArgumentParser:
    profiles = list_profile_names()
    p = argparse.ArgumentParser(
        prog="smart-convert",
        description=(
            "Сжимает видеокурс: тест HEVC vs AV1 на сэмпле (NVENC или CPU), "
            "затем полный encode при достаточной экономии места."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    p.add_argument("input", type=Path, help="Путь к видеофайлу")
    p.add_argument(
        "--profile",
        default="default",
        choices=profiles,
        help="Named preset from profiles.toml (CLI flags override)",
    )
    p.add_argument(
        "--sample-sec",
        type=float,
        default=None,
        help="Длина тестового фрагмента (сек; default: from profile)",
    )
    p.add_argument(
        "--offset-ratio",
        type=float,
        default=None,
        help="Старт сэмпла как доля длительности (default: from profile)",
    )
    p.add_argument(
        "--min-savings",
        type=float,
        default=None,
        help="Минимальная прогнозная экономия (default: from profile)",
    )
    p.add_argument(
        "--cq-hevc",
        type=int,
        default=None,
        help="CQ/CRF для HEVC (default: from profile)",
    )
    p.add_argument(
        "--cq-av1",
        type=int,
        default=None,
        help="CQ/CRF для AV1 (default: from profile)",
    )
    p.add_argument(
        "--preset",
        default=None,
        help="NVENC preset p1..p7 (CPU: mapped to x265/SVT; default: from profile)",
    )
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
        help="Hybrid VMAF for sample race: off | auto (if libvmaf) | on (default: from profile)",
    )
    p.add_argument(
        "--vmaf-min",
        type=float,
        default=None,
        help="Min VMAF to prefer smaller codec among candidates (default: from profile)",
    )
    p.add_argument(
        "--sample-fragments",
        type=int,
        default=None,
        help="Number of sample clips to average (default: from profile, usually 1)",
    )
    p.add_argument(
        "--nvenc-multipass",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable NVENC -multipass fullres (off by default; slower)",
    )
    p.add_argument(
        "--nvenc-lookahead",
        type=int,
        default=None,
        help="NVENC -rc-lookahead frames (0=off; default: from profile)",
    )
    p.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Append app log lines to this file (in addition to stdout)",
    )
    p.add_argument(
        "--audio",
        default=None,
        help="Аудио финального файла: copy | aac[:kbps] | opus[:kbps] (default: from profile)",
    )
    p.add_argument(
        "--force-codec",
        choices=["hevc", "av1"],
        default=None,
        help="Пропустить выбор: сразу этот кодек",
    )
    p.add_argument("--dry-run", action="store_true", help="Только бенчмарк сэмпла, без полного encode")
    p.add_argument("--keep-samples", action="store_true", help="Сохранить тестовые фрагменты рядом с файлом")
    p.add_argument(
        "--reencode-same-codec",
        action="store_true",
        help="Не пропускать файлы, которые уже HEVC/AV1 (или уже force-codec)",
    )
    return p


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def main(argv: list[str] | None = None) -> int:
    ensure_long_paths()
    args = build_parser().parse_args(argv)
    try:
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
            keep_samples=args.keep_samples,
            skip_same_codec=not args.reencode_same_codec,
        )
        log = tee_log(_safe_print, args.log_file)
        for line in validate_environment(settings.encoder):
            log(f"env: {line}")
        convert_one(args.input, settings, log=log)
        return 0
    except (ToolError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
