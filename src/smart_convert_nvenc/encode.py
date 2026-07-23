from __future__ import annotations

from pathlib import Path

from .ffmpeg_runner import ProgressCallback, run_ffmpeg
from .models import AudioMode, AudioSettings, EncodeProfile, VideoCodec


def audio_args(settings: AudioSettings, *, for_sample: bool) -> list[str]:
    # Samples always copy audio so size comparison is about video only.
    if for_sample or settings.mode is AudioMode.COPY:
        return ["-c:a", "copy"]
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
) -> list[str]:
    args: list[str] = ["-hwaccel", "auto"]
    if seek_seconds > 0:
        args.extend(["-ss", f"{seek_seconds:.3f}"])
    args.extend(["-i", str(input_path)])
    if sample_seconds is not None:
        args.extend(["-t", f"{sample_seconds:.3f}"])
    args.extend(["-map", "0:v:0"])
    args.extend(["-map", "0:a:0?"])
    args.extend(video_args(profile))
    args.extend(audio_args(audio, for_sample=for_sample))
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
) -> float:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    args = build_encode_args(
        input_path=input_path,
        output_path=output_path,
        profile=profile,
        audio=audio,
        sample_seconds=sample_seconds,
        seek_seconds=seek_seconds,
        for_sample=for_sample,
    )
    return run_ffmpeg(args, on_progress=on_progress)
