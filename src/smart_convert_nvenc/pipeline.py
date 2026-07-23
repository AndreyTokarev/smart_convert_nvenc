from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from .encode import encode_file
from .models import (
    DISCLAIMER_SIZE_AT_CQ,
    BenchmarkReport,
    ConvertSettings,
    EncodeProfile,
    MediaInfo,
    SampleResult,
    VideoCodec,
)
from .probe import probe_media, require_nvenc


LogFn = Callable[[str], None]


def _log(log: LogFn | None, message: str) -> None:
    if log:
        log(message)


def _format_mb(size: int) -> str:
    return f"{size / (1024 * 1024):.2f} МиБ"


def sample_seek_seconds(info: MediaInfo, settings: ConvertSettings) -> float:
    if info.duration_sec <= settings.sample_seconds:
        return 0.0
    max_start = max(0.0, info.duration_sec - settings.sample_seconds)
    return min(max_start, info.duration_sec * settings.sample_offset_ratio)


def run_sample(
    *,
    input_path: Path,
    work_dir: Path,
    profile: EncodeProfile,
    settings: ConvertSettings,
    seek: float,
    log: LogFn | None = None,
) -> SampleResult:
    out = work_dir / f"sample_{profile.codec.value}{profile.container_ext}"
    _log(log, f"Тест {profile.codec.value.upper()} NVENC (CQ={profile.cq}, preset={profile.preset})...")
    elapsed = encode_file(
        input_path=input_path,
        output_path=out,
        profile=profile,
        audio=settings.audio,
        sample_seconds=settings.sample_seconds,
        seek_seconds=seek,
        for_sample=True,
        on_progress=lambda line: _log(log, f"  {line}"),
    )
    size = out.stat().st_size
    _log(log, f"  -> {_format_mb(size)} за {elapsed:.1f} с")
    return SampleResult(profile=profile, path=str(out), size_bytes=size, elapsed_sec=elapsed)


def choose_winner(
    *,
    hevc: SampleResult,
    av1: SampleResult,
    original_bytes: int,
    duration_sec: float,
    sample_seconds: float,
    min_savings: float,
    force_codec: VideoCodec | None,
) -> BenchmarkReport:
    if force_codec is VideoCodec.HEVC:
        winner = hevc
    elif force_codec is VideoCodec.AV1:
        winner = av1
    else:
        winner = av1 if av1.size_bytes < hevc.size_bytes else hevc

    scale = duration_sec / sample_seconds if sample_seconds > 0 else 1.0
    projected = int(winner.size_bytes * scale)
    savings = 1.0 - (projected / original_bytes) if original_bytes > 0 else 0.0
    worth = projected < original_bytes * (1.0 - min_savings)

    return BenchmarkReport(
        winner=winner.profile,
        hevc=hevc,
        av1=av1,
        projected_full_bytes=projected,
        original_bytes=original_bytes,
        savings_ratio=savings,
        worth_encoding=worth,
        disclaimer=DISCLAIMER_SIZE_AT_CQ,
    )


def output_path_for(input_path: Path, profile: EncodeProfile) -> Path:
    return input_path.with_name(f"{input_path.stem}_nvenc_{profile.codec.value}{profile.container_ext}")


def convert_one(
    input_path: Path,
    settings: ConvertSettings,
    *,
    log: LogFn | None = None,
) -> Path | None:
    require_nvenc()
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    info = probe_media(input_path)
    _log(log, f"Исходник: {input_path.name}")
    _log(
        log,
        f"  {_format_mb(info.size_bytes)}, {info.duration_sec:.1f} с, "
        f"видео={info.video_codec or '?'}, "
        f"{info.width or '?'}x{info.height or '?'}",
    )
    if info.duration_sec <= 0:
        raise RuntimeError("Не удалось определить длительность видео (ffprobe).")

    seek = sample_seek_seconds(info, settings)
    sample_len = min(settings.sample_seconds, info.duration_sec)
    _log(log, f"Сэмпл: {sample_len:.0f} с с позиции {seek:.1f} с ({settings.sample_offset_ratio:.0%} длительности)")
    _log(log, f"[!] {DISCLAIMER_SIZE_AT_CQ}")

    with tempfile.TemporaryDirectory(prefix="smart_convert_") as tmp:
        work = Path(tmp)
        hevc = run_sample(
            input_path=input_path,
            work_dir=work,
            profile=settings.hevc_profile(),
            settings=settings,
            seek=seek,
            log=log,
        )
        av1 = run_sample(
            input_path=input_path,
            work_dir=work,
            profile=settings.av1_profile(),
            settings=settings,
            seek=seek,
            log=log,
        )

        report = choose_winner(
            hevc=hevc,
            av1=av1,
            original_bytes=info.size_bytes,
            duration_sec=info.duration_sec,
            sample_seconds=sample_len,
            min_savings=settings.min_savings,
            force_codec=settings.force_codec,
        )

        _log(log, "=" * 50)
        _log(log, f"HEVC sample: {_format_mb(hevc.size_bytes)}")
        _log(log, f"AV1  sample: {_format_mb(av1.size_bytes)}")
        _log(log, f"Победитель: {report.winner.codec.value.upper()} NVENC")
        _log(
            log,
            f"Прогноз полного файла: {_format_mb(report.projected_full_bytes)} "
            f"(исходник {_format_mb(report.original_bytes)}, "
            f"экономия {report.savings_ratio * 100:.1f}%)",
        )

        if settings.keep_samples:
            keep_dir = input_path.parent / f".smart_convert_samples_{input_path.stem}"
            keep_dir.mkdir(exist_ok=True)
            for sample in (hevc, av1):
                dest = keep_dir / Path(sample.path).name
                dest.write_bytes(Path(sample.path).read_bytes())
            _log(log, f"Сэмплы сохранены в {keep_dir}")

        if not report.worth_encoding:
            _log(
                log,
                f"Пропуск полного encode: прогноз экономии < {settings.min_savings * 100:.0f}% "
                f"(или файл не станет заметно меньше).",
            )
            return None

        out = output_path_for(input_path, report.winner)
        if settings.dry_run:
            _log(log, f"Dry-run: полный encode не запускался. Был бы файл: {out}")
            return out

        _log(log, f"Полное кодирование -> {out.name}")
        encode_file(
            input_path=input_path,
            output_path=out,
            profile=report.winner,
            audio=settings.audio,
            for_sample=False,
            on_progress=lambda line: _log(log, f"  {line}"),
        )
        final_size = out.stat().st_size
        real_savings = 1.0 - (final_size / info.size_bytes)
        _log(
            log,
            f"Готово: {_format_mb(final_size)} "
            f"(факт. экономия {real_savings * 100:.1f}%)\n{out}",
        )
        return out
