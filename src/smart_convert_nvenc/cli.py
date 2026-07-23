from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .models import AudioSettings, ConvertSettings, VideoCodec
from .pipeline import convert_one
from .probe import ToolError, validate_environment


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="smart-convert",
        description=(
            "Сжимает видеокурс через NVIDIA NVENC: тест HEVC vs AV1 на сэмпле, "
            "затем полный encode при достаточной экономии места."
        ),
    )
    p.add_argument("input", type=Path, help="Путь к видеофайлу")
    p.add_argument("--sample-sec", type=float, default=30.0, help="Длина тестового фрагмента (сек)")
    p.add_argument(
        "--offset-ratio",
        type=float,
        default=0.25,
        help="Старт сэмпла как доля длительности (0.25 = 25%%)",
    )
    p.add_argument(
        "--min-savings",
        type=float,
        default=0.10,
        help="Минимальная прогнозная экономия (0.10 = 10%%), иначе skip",
    )
    p.add_argument("--cq-hevc", type=int, default=28, help="CQ для hevc_nvenc")
    p.add_argument("--cq-av1", type=int, default=32, help="CQ для av1_nvenc")
    p.add_argument("--preset", default="p6", help="NVENC preset p1..p7")
    p.add_argument(
        "--audio",
        default="copy",
        help="Аудио финального файла: copy | aac[:kbps] | opus[:kbps]",
    )
    p.add_argument(
        "--force-codec",
        choices=["hevc", "av1"],
        default=None,
        help="Пропустить выбор: сразу этот кодек",
    )
    p.add_argument("--dry-run", action="store_true", help="Только бенчмарк сэмпла, без полного encode")
    p.add_argument("--keep-samples", action="store_true", help="Сохранить тестовые фрагменты рядом с файлом")
    return p


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        for line in validate_environment():
            _safe_print(f"env: {line}")
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
            keep_samples=args.keep_samples,
        )
        convert_one(args.input, settings, log=_safe_print)
        return 0
    except (ToolError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
