from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from .encode import encode_file
from .ffmpeg_runner import FFmpegCancelled, StopCheck
from .models import (
    DISCLAIMER_SIZE_AT_CQ,
    DISCLAIMER_VMAF,
    BenchmarkReport,
    ConvertSettings,
    EncoderBackend,
    EncodeProfile,
    MediaInfo,
    SampleResult,
    VideoCodec,
    VideoDecision,
    VmafMode,
    already_target_codec,
)
from .probe import (
    ToolError,
    has_av1_nvenc,
    has_cpu_encoders,
    probe_media,
    resolve_encoder_backend,
)
from .progress import clamp01, parse_ffmpeg_speed, parse_ffmpeg_time_seconds
from .vmaf import has_libvmaf, score_vmaf


LogFn = Callable[[str], None]
# phase name, fraction within that phase 0..1, optional ffmpeg speed multiplier
PhaseProgressFn = Callable[[str, float, float | None], None]


def _av1_profile_for_backend(
    settings: ConvertSettings, backend: EncoderBackend
) -> EncodeProfile:
    """AV1 profile: prefer NVENC; if missing, fall back to libsvtav1 (CPU)."""
    if backend is EncoderBackend.CPU:
        return settings.av1_profile(backend=EncoderBackend.CPU)
    if has_av1_nvenc():
        return settings.av1_profile(backend=EncoderBackend.GPU)
    if has_cpu_encoders():
        return settings.av1_profile(backend=EncoderBackend.CPU)
    raise ToolError(
        "Нужен AV1, но нет ни av1_nvenc, ни libsvtav1 в FFmpeg. "
        "Поставьте полную сборку FFmpeg или выберите HEVC."
    )


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


def sample_seek_list(info: MediaInfo, settings: ConvertSettings) -> list[float]:
    """Seek starts for sample fragments. N=1 matches ``sample_seek_seconds``."""
    n = max(1, int(settings.sample_fragments))
    if n == 1:
        return [sample_seek_seconds(info, settings)]
    if info.duration_sec <= settings.sample_seconds:
        return [0.0] * n
    max_start = max(0.0, info.duration_sec - settings.sample_seconds)
    if n == 1 or max_start <= 0:
        return [0.0]
    # Evenly spaced from 0 .. max_start (inclusive endpoints)
    return [max_start * i / (n - 1) for i in range(n)]


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
    fragment_index: int = 0,
) -> SampleResult:
    stem = f"sample_{profile.codec.value}"
    if fragment_index:
        stem = f"{stem}_{fragment_index}"
    out = work_dir / f"{stem}{profile.container_ext}"
    backend_label = profile.backend.value
    quality = "CRF" if profile.backend is EncoderBackend.CPU else "CQ"
    _log(
        log,
        f"  sample {profile.codec.value.upper()} "
        f"({backend_label}, {quality}={profile.cq}, preset={profile.preset}"
        f"{f', frag={fragment_index + 1}' if fragment_index or settings.sample_fragments > 1 else ''}"
        f")...",
    )
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


def run_samples_averaged(
    *,
    input_path: Path,
    work_dir: Path,
    profile: EncodeProfile,
    settings: ConvertSettings,
    seeks: list[float],
    sample_seconds: float,
    want_vmaf: bool,
    log: LogFn | None = None,
    on_progress: Callable[[str], None] | None = None,
    should_stop: StopCheck | None = None,
) -> SampleResult:
    """Encode one or more sample fragments; average size (and VMAF if requested)."""
    sizes: list[int] = []
    vmafs: list[float] = []
    elapsed_total = 0.0
    last_path = ""
    for i, seek in enumerate(seeks):
        sample = run_sample(
            input_path=input_path,
            work_dir=work_dir,
            profile=profile,
            settings=settings,
            seek=seek,
            log=log,
            on_progress=on_progress,
            should_stop=should_stop,
            fragment_index=i if len(seeks) > 1 else 0,
        )
        sizes.append(sample.size_bytes)
        elapsed_total += sample.elapsed_sec
        last_path = sample.path
        if want_vmaf:
            scored = _with_vmaf(
                sample,
                reference=input_path,
                seek=seek,
                sample_seconds=sample_seconds,
                log=log,
                should_stop=should_stop,
            )
            if scored.vmaf is not None:
                vmafs.append(scored.vmaf)
    avg_size = int(sum(sizes) / len(sizes))
    avg_vmaf = (sum(vmafs) / len(vmafs)) if vmafs else None
    if len(seeks) > 1:
        _log(
            log,
            f"    avg over {len(seeks)} fragments: {_format_mb(avg_size)}"
            + (f", VMAF={avg_vmaf:.2f}" if avg_vmaf is not None else ""),
        )
    return SampleResult(
        profile=profile,
        path=last_path,
        size_bytes=avg_size,
        elapsed_sec=elapsed_total,
        vmaf=avg_vmaf,
    )


def choose_winner(
    *,
    hevc: SampleResult | None,
    av1: SampleResult | None,
    original_bytes: int,
    duration_sec: float,
    sample_seconds: float,
    min_savings: float,
    force_profile: EncodeProfile | None,
    vmaf_min: float = 90.0,
) -> BenchmarkReport:
    if force_profile is not None:
        return BenchmarkReport(
            winner=force_profile,
            hevc=hevc,
            av1=av1,
            projected_full_bytes=original_bytes,
            original_bytes=original_bytes,
            savings_ratio=0.0,
            worth_encoding=True,
            disclaimer=DISCLAIMER_SIZE_AT_CQ,
        )

    if hevc is None and av1 is None:
        raise ValueError("Need at least one sample result (hevc and/or av1)")

    samples = [s for s in (hevc, av1) if s is not None]
    use_vmaf = len(samples) > 1 and all(s.vmaf is not None for s in samples)
    disclaimer = DISCLAIMER_VMAF if use_vmaf else DISCLAIMER_SIZE_AT_CQ

    if hevc is None:
        winner_sample = av1
        assert winner_sample is not None
    elif av1 is None:
        winner_sample = hevc
    elif use_vmaf:
        assert hevc.vmaf is not None and av1.vmaf is not None
        above = [s for s in (hevc, av1) if s.vmaf >= vmaf_min]
        if above:
            winner_sample = min(above, key=lambda s: s.size_bytes)
        else:
            winner_sample = hevc if hevc.vmaf >= av1.vmaf else av1
    else:
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
        disclaimer=disclaimer,
    )


def _want_vmaf(settings: ConvertSettings) -> bool:
    if settings.vmaf is VmafMode.OFF:
        return False
    if settings.vmaf is VmafMode.ON:
        if not has_libvmaf():
            raise ToolError(
                "VMAF=on, но в FFmpeg нет libvmaf. "
                "Поставьте сборку с libvmaf или --vmaf auto/off."
            )
        return True
    if settings.vmaf is VmafMode.AUTO:
        return has_libvmaf()
    raise AssertionError(f"Unhandled VmafMode: {settings.vmaf}")


def _with_vmaf(
    sample: SampleResult,
    *,
    reference: Path,
    seek: float,
    sample_seconds: float,
    log: LogFn | None,
    should_stop: StopCheck | None,
) -> SampleResult:
    try:
        score = score_vmaf(
            reference=reference,
            distorted=Path(sample.path),
            seek_seconds=seek,
            sample_seconds=sample_seconds,
            should_stop=should_stop,
        )
    except ToolError as exc:
        _log(log, f"    VMAF skipped ({exc})")
        return sample
    _log(log, f"    VMAF={score:.2f}")
    return replace(sample, vmaf=score)


def output_path_for(input_path: Path, profile: EncodeProfile) -> Path:
    tag = "nvenc" if profile.backend is EncoderBackend.GPU else "cpu"
    return input_path.with_name(
        f"{input_path.stem}_{tag}_{profile.codec.value}{profile.container_ext}"
    )


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
    backend, backend_note = resolve_encoder_backend(settings.encoder)
    _log(log, f"  {backend_note}")
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
        if settings.force_codec is VideoCodec.HEVC:
            effective_force = settings.hevc_profile(backend=backend)
        else:
            effective_force = _av1_profile_for_backend(settings, backend)
    elif effective_force is not None and effective_force.backend is EncoderBackend.AUTO:
        if effective_force.codec is VideoCodec.AV1:
            effective_force = _av1_profile_for_backend(settings, backend)
        else:
            effective_force = EncodeProfile(
                codec=effective_force.codec,
                cq=effective_force.cq,
                preset=effective_force.preset,
                container_ext=effective_force.container_ext,
                backend=backend,
                multipass=effective_force.multipass,
                rc_lookahead=effective_force.rc_lookahead,
            )

    if (
        effective_force is not None
        and effective_force.codec is VideoCodec.AV1
        and effective_force.backend is EncoderBackend.CPU
        and backend is EncoderBackend.GPU
    ):
        _log(
            log,
            "  AV1 via libsvtav1 (cpu) — av1_nvenc not in this FFmpeg build",
        )

    def _emit_phase(phase: str, local: float, speed: float | None = None) -> None:
        if on_phase_progress:
            on_phase_progress(phase, clamp01(local), speed)

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

    seeks = sample_seek_list(info, settings)
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
            speed = parse_ffmpeg_speed(line)
            t = parse_ffmpeg_time_seconds(line)
            if t is not None and duration > 0:
                _emit_phase(phase, t / duration, speed)

        return _cb

    with tempfile.TemporaryDirectory(prefix="smart_convert_sample_") as tmp:
        work = Path(tmp)
        hevc: SampleResult | None = None
        av1: SampleResult | None = None

        if racing:
            want_vmaf = _want_vmaf(settings)
            _log(log, f"  [!] {DISCLAIMER_VMAF if want_vmaf else DISCLAIMER_SIZE_AT_CQ}")
            if len(seeks) > 1:
                _log(log, f"  sample fragments: {len(seeks)}")
            hevc = run_samples_averaged(
                input_path=input_path,
                work_dir=work,
                profile=settings.hevc_profile(backend=backend),
                settings=settings,
                seeks=seeks,
                sample_seconds=sample_len,
                want_vmaf=want_vmaf,
                log=log,
                on_progress=_make_ffmpeg_cb("sample_hevc", sample_len),
                should_stop=should_stop,
            )
            _emit_phase("sample_hevc", 1.0)
            try:
                av1_profile = _av1_profile_for_backend(settings, backend)
            except ToolError as exc:
                _log(log, f"  skip AV1 sample ({exc})")
                av1_profile = None
            if av1_profile is not None:
                if (
                    backend is EncoderBackend.GPU
                    and av1_profile.backend is EncoderBackend.CPU
                ):
                    _log(
                        log,
                        "  AV1 sample via libsvtav1 (cpu) — no av1_nvenc in FFmpeg",
                    )
                av1 = run_samples_averaged(
                    input_path=input_path,
                    work_dir=work,
                    profile=av1_profile,
                    settings=settings,
                    seeks=seeks,
                    sample_seconds=sample_len,
                    want_vmaf=want_vmaf,
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
            vmaf_min=settings.vmaf_min,
        )

        if hevc and av1:
            bits = [
                f"winner={report.winner.codec.value.upper()}",
                f"proj={_format_mb(report.projected_full_bytes)}",
                f"({report.savings_ratio * 100:.1f}% vs source)",
            ]
            if hevc.vmaf is not None and av1.vmaf is not None:
                bits.append(f"VMAF hevc={hevc.vmaf:.1f} av1={av1.vmaf:.1f}")
            _log(log, "  " + " ".join(bits))

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
