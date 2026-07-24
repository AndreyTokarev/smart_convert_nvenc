from __future__ import annotations

from pathlib import Path

from .ffmpeg_runner import FFmpegCancelled, FFmpegError, ProgressCallback, StopCheck, run_ffmpeg
from .models import AudioMode, AudioSettings, EncodeProfile, VideoCodec
from .temp_paths import make_conversion_temp, promote_temp_to_final

# MPEG-TS / similar often carry AAC in ADTS; MP4/MKV need ASC when copying.
_ADTS_INPUT_SUFFIXES = {".ts", ".mts", ".m2ts", ".mpeg", ".mpg"}


def audio_args(
    settings: AudioSettings,
    *,
    for_sample: bool,
    input_path: Path | None = None,
    output_path: Path | None = None,
) -> list[str]:
    # Samples compare video size only — drop audio so MPEG-TS seek + MKV/AV1
    # does not fail on broken AAC extradata, and CQ race stays video-pure.
    if for_sample:
        return ["-an"]
    if settings.mode is AudioMode.COPY:
        args = ["-c:a", "copy"]
        if (
            input_path is not None
            and output_path is not None
            and input_path.suffix.lower() in _ADTS_INPUT_SUFFIXES
            and output_path.suffix.lower() in {".mp4", ".m4v", ".mov", ".mkv"}
        ):
            args.extend(["-bsf:a", "aac_adtstoasc"])
        return args
    if settings.mode is AudioMode.AAC:
        return ["-c:a", "aac", "-b:a", f"{settings.bitrate_k}k"]
    if settings.mode is AudioMode.OPUS:
        return ["-c:a", "libopus", "-b:a", f"{settings.bitrate_k}k"]
    raise AssertionError(f"Unhandled audio mode: {settings.mode}")


def video_args(profile: EncodeProfile) -> list[str]:
    args = [
        "-c:v",
        profile.nvenc_name,
        "-preset",
        profile.preset,
        "-tune",
        "hq",
        "-rc",
        "vbr",
        "-cq",
        str(profile.cq),
        "-b:v",
        "0",
        "-spatial_aq",
        "1",
        "-temporal_aq",
        "1",
    ]
    if profile.codec is VideoCodec.HEVC:
        args.extend(["-tag:v", "hvc1"])
    return args


def build_encode_args(
    *,
    input_path: Path,
    output_path: Path,
    profile: EncodeProfile,
    audio: AudioSettings,
    sample_seconds: float | None = None,
    seek_seconds: float = 0.0,
    for_sample: bool = False,
    hwaccel: str | None = "auto",
) -> list[str]:
    args: list[str] = []
    if hwaccel:
        args.extend(["-hwaccel", hwaccel])
    if seek_seconds > 0:
        args.extend(["-ss", f"{seek_seconds:.3f}"])
    args.extend(["-i", str(input_path)])
    if sample_seconds is not None:
        args.extend(["-t", f"{sample_seconds:.3f}"])
    args.extend(["-map", "0:v:0"])
    if not for_sample:
        args.extend(["-map", "0:a:0?"])
    args.extend(video_args(profile))
    args.extend(
        audio_args(
            audio,
            for_sample=for_sample,
            input_path=input_path,
            output_path=output_path,
        )
    )
    args.append(str(output_path))
    return args


def encode_file(
    *,
    input_path: Path,
    output_path: Path,
    profile: EncodeProfile,
    audio: AudioSettings,
    sample_seconds: float | None = None,
    seek_seconds: float = 0.0,
    for_sample: bool = False,
    on_progress: ProgressCallback | None = None,
    should_stop: StopCheck | None = None,
    use_temp: bool = True,
    retry_without_hwaccel: bool = True,
) -> float:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target = make_conversion_temp(output_path) if use_temp else output_path

    def _run(hwaccel: str | None) -> float:
        args = build_encode_args(
            input_path=input_path,
            output_path=target,
            profile=profile,
            audio=audio,
            sample_seconds=sample_seconds,
            seek_seconds=seek_seconds,
            for_sample=for_sample,
            hwaccel=hwaccel,
        )
        return run_ffmpeg(args, on_progress=on_progress, should_stop=should_stop)

    try:
        try:
            elapsed = _run("auto")
        except FFmpegCancelled:
            if target != output_path and target.exists():
                target.unlink(missing_ok=True)
            raise
        except FFmpegError:
            if not retry_without_hwaccel:
                if target != output_path and target.exists():
                    target.unlink(missing_ok=True)
                raise
            if target.exists():
                target.unlink(missing_ok=True)
            elapsed = _run(None)
    except Exception:
        if target != output_path and target.exists():
            target.unlink(missing_ok=True)
        raise

    if use_temp:
        promote_temp_to_final(target, output_path)
    return elapsed
