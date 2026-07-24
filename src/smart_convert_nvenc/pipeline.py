from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from .encode import encode_file
from .ffmpeg_runner import FFmpegCancelled, StopCheck
from .models import (
    DISCLAIMER_SIZE_AT_CQ,
    BenchmarkReport,
    ConvertSettings,
    EncodeProfile,
    MediaInfo,
    SampleResult,
    VideoCodec,
    VideoDecision,
    already_target_codec,
)
from .probe import probe_media, require_nvenc
from .progress import clamp01, parse_ffmpeg_time_seconds


LogFn = Callable[[str], None]
# phase name, fraction within that phase 0..1
PhaseProgressFn = Callable[[str, float], None]


def _log(log: LogFn | None, message: str) -> None:
    if log:
        log(message)


def _format_mb(size: int) -> str:
    return f"{size / (1024 * 1024):.2f} MiB"


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
    on_progress: Callable[[str], None] | None = None,
    should_stop: StopCheck | None = None,
) -> SampleResult:
    out = work_dir / f"sample_{profile.codec.value}{profile.container_ext}"
    _log(log, f"  sample {profile.codec.value.upper()} (CQ={profile.cq}, preset={profile.preset})...")
    elapsed = encode_file(
        input_path=input_path,
        output_path=out,
        profile=profile,
        audio=settings.audio,
        sample_seconds=settings.sample_seconds,
        seek_seconds=seek,
        for_sample=True,
        on_progress=on_progress,
        should_stop=should_stop,
    )
    size = out.stat().st_size
    _log(log, f"    -> {_format_mb(size)} in {elapsed:.1f}s")
    return SampleResult(profile=profile, path=str(out), size_bytes=size, elapsed_sec=elapsed)


def choose_winner(
    *,
    hevc: SampleResult | None,
    av1: SampleResult | None,
    original_bytes: int,
    duration_sec: float,
    sample_seconds: float,
    min_savings: float,
    force_profile: EncodeProfile | None,
) -> BenchmarkReport:
    if force_profile is not None:
        # Size projection unavailable without a sample; treat as worth trying full encode.
        # Caller should still compare actual output size.
        projected = original_bytes
        winner = force_profile
        savings = 0.0
        worth = True
        return BenchmarkReport(
            winner=winner,
            hevc=hevc,
            av1=av1,
            projected_full_bytes=projected,
            original_bytes=original_bytes,
            savings_ratio=savings,
            worth_encoding=worth,
            disclaimer=DISCLAIMER_SIZE_AT_CQ,
        )

    assert hevc is not None and av1 is not None
    winner_sample = av1 if av1.size_bytes < hevc.size_bytes else hevc
    scale = duration_sec / sample_seconds if sample_seconds > 0 else 1.0
    projected = int(winner_sample.size_bytes * scale)
    savings = 1.0 - (projected / original_bytes) if original_bytes > 0 else 0.0
    worth = projected < original_bytes * (1.0 - min_savings)

    return BenchmarkReport(
        winner=winner_sample.profile,
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


def convert_video(
    input_path: Path,
    settings: ConvertSettings,
    *,
    output_path: Path | None = None,
    force_profile: EncodeProfile | None = None,
    log: LogFn | None = None,
    show_encode_progress: bool = False,
    on_ffmpeg_progress: LogFn | None = None,
    on_phase_progress: PhaseProgressFn | None = None,
    should_stop: StopCheck | None = None,
) -> VideoDecision:
    """Benchmark (unless force_profile) and optionally full-encode one video."""
    require_nvenc()
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if should_stop and should_stop():
        raise FFmpegCancelled("Stopped by user")

    info = probe_media(input_path)
    _log(
        log,
        f"{input_path.name}: {_format_mb(info.size_bytes)}, "
        f"{info.duration_sec:.1f}s, {info.video_codec or '?'}, "
        f"{info.width or '?'}x{info.height or '?'}",
    )
    if info.duration_sec <= 0:
        raise RuntimeError(f"Cannot read duration: {input_path}")

    effective_force = force_profile
    if effective_force is None and settings.force_codec is not None:
        effective_force = (
            settings.hevc_profile()
            if settings.force_codec is VideoCodec.HEVC
            else settings.av1_profile()
        )

    def _emit_phase(phase: str, local: float) -> None:
        if on_phase_progress:
            on_phase_progress(phase, clamp01(local))

    if settings.skip_same_codec:
        target = effective_force.codec if effective_force is not None else None
        matched = already_target_codec(info.video_codec, force=target)
        if matched is not None:
            _log(
                log,
                f"  skip encode (already {matched.value}: {info.video_codec})",
            )
            _emit_phase("done", 1.0)
            return VideoDecision(
                source=input_path,
                original_size=info.size_bytes,
                compressed=False,
                output=input_path,
                profile=None,
                projected_or_final_size=info.size_bytes,
            )

    seek = sample_seek_seconds(info, settings)
    sample_len = min(settings.sample_seconds, info.duration_sec)
    racing = effective_force is None

    def _make_ffmpeg_cb(phase: str, duration: float) -> Callable[[str], None] | None:
        if not on_ffmpeg_progress and not on_phase_progress and not show_encode_progress:
            return None

        def _cb(line: str) -> None:
            if on_ffmpeg_progress:
                on_ffmpeg_progress(line)
            elif show_encode_progress:
                _log(log, f"    {line}")
            t = parse_ffmpeg_time_seconds(line)
            if t is not None and duration > 0:
                _emit_phase(phase, t / duration)

        return _cb

    with tempfile.TemporaryDirectory(prefix="smart_convert_sample_") as tmp:
        work = Path(tmp)
        hevc: SampleResult | None = None
        av1: SampleResult | None = None

        if racing:
            _log(log, f"  [!] {DISCLAIMER_SIZE_AT_CQ}")
            hevc = run_sample(
                input_path=input_path,
                work_dir=work,
                profile=settings.hevc_profile(),
                settings=settings,
                seek=seek,
                log=log,
                on_progress=_make_ffmpeg_cb("sample_hevc", sample_len),
                should_stop=should_stop,
            )
            _emit_phase("sample_hevc", 1.0)
            av1 = run_sample(
                input_path=input_path,
                work_dir=work,
                profile=settings.av1_profile(),
                settings=settings,
                seek=seek,
                log=log,
                on_progress=_make_ffmpeg_cb("sample_av1", sample_len),
                should_stop=should_stop,
            )
            _emit_phase("sample_av1", 1.0)

        report = choose_winner(
            hevc=hevc,
            av1=av1,
            original_bytes=info.size_bytes,
            duration_sec=info.duration_sec,
            sample_seconds=sample_len,
            min_savings=settings.min_savings,
            force_profile=effective_force,
        )

        if hevc and av1:
            _log(
                log,
                f"  winner={report.winner.codec.value.upper()} "
                f"proj={_format_mb(report.projected_full_bytes)} "
                f"({report.savings_ratio * 100:.1f}% vs source)",
            )

        if not report.worth_encoding and effective_force is None:
            _log(log, "  skip full encode (projected savings too low)")
            _emit_phase("done", 1.0)
            return VideoDecision(
                source=input_path,
                original_size=info.size_bytes,
                compressed=False,
                output=input_path,
                profile=None,
                projected_or_final_size=info.size_bytes,
            )

        if output_path is not None:
            out = output_path.with_suffix(report.winner.container_ext)
        else:
            out = output_path_for(input_path, report.winner)
        if settings.dry_run:
            _log(log, f"  dry-run: would write {out}")
            _emit_phase("done", 1.0)
            return VideoDecision(
                source=input_path,
                original_size=info.size_bytes,
                compressed=True,
                output=out,
                profile=report.winner,
                projected_or_final_size=report.projected_full_bytes,
            )

        _log(log, f"  encoding full -> {out.name}")
        encode_file(
            input_path=input_path,
            output_path=out,
            profile=report.winner,
            audio=settings.audio,
            for_sample=False,
            on_progress=_make_ffmpeg_cb("encode", info.duration_sec),
            should_stop=should_stop,
        )
        _emit_phase("encode", 1.0)
        final_size = out.stat().st_size
        if final_size >= info.size_bytes * (1.0 - settings.min_savings):
            _log(
                log,
                f"  compressed not worth keeping "
                f"({_format_mb(final_size)} vs {_format_mb(info.size_bytes)}); keep original",
            )
            out.unlink(missing_ok=True)
            _emit_phase("done", 1.0)
            return VideoDecision(
                source=input_path,
                original_size=info.size_bytes,
                compressed=False,
                output=input_path,
                profile=report.winner,
                projected_or_final_size=info.size_bytes,
            )

        real_savings = 1.0 - (final_size / info.size_bytes)
        _log(log, f"  done {_format_mb(final_size)} ({real_savings * 100:.1f}% smaller)")
        _emit_phase("done", 1.0)
        return VideoDecision(
            source=input_path,
            original_size=info.size_bytes,
            compressed=True,
            output=out,
            profile=report.winner,
            projected_or_final_size=final_size,
        )


def convert_one(
    input_path: Path,
    settings: ConvertSettings,
    *,
    log: LogFn | None = None,
) -> Path | None:
    decision = convert_video(
        input_path,
        settings,
        log=log,
        show_encode_progress=True,
    )
    return decision.output if decision.compressed else None
