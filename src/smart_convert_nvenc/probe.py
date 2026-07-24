from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .ffmpeg_tools import describe_tools, ffmpeg_executable, ffprobe_executable, resolve_tool
from .models import EncoderBackend, MediaInfo


class ToolError(RuntimeError):
    pass


def require_tools() -> None:
    missing: list[str] = []
    for name in ("ffmpeg", "ffprobe"):
        try:
            resolve_tool(name)
        except FileNotFoundError:
            missing.append(name)
    if missing:
        joined = ", ".join(f"`{n}`" for n in missing)
        raise ToolError(
            f"Не найден {joined}. Положите FFmpeg в ffmpeg/bin рядом с приложением "
            "или установите в PATH (например gyan.dev / BtbN)."
        )


def list_ffmpeg_encoders() -> set[str]:
    require_tools()
    result = subprocess.run(
        [ffmpeg_executable(), "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = (result.stdout or "") + (result.stderr or "")
    names: set[str] = set()
    for line in text.splitlines():
        # Typical: " V....D libx265              ..."
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("V"):
            names.add(parts[1])
    # Also accept substring matches for older/odd listings
    for needle in (
        "hevc_nvenc",
        "av1_nvenc",
        "libx265",
        "libsvtav1",
    ):
        if needle in text:
            names.add(needle)
    return names


def has_nvenc(encoders: set[str] | None = None) -> bool:
    names = encoders if encoders is not None else list_ffmpeg_encoders()
    return "hevc_nvenc" in names and "av1_nvenc" in names


def has_cpu_encoders(encoders: set[str] | None = None) -> bool:
    names = encoders if encoders is not None else list_ffmpeg_encoders()
    return "libx265" in names and "libsvtav1" in names


def require_nvenc() -> None:
    if not has_nvenc():
        raise ToolError(
            "FFmpeg без нужных NVENC-энкодеров: hevc_nvenc, av1_nvenc. "
            "Нужна сборка с NVENC и GPU RTX 40xx (для AV1 encode), "
            "либо используйте --encoder cpu / auto."
        )


def require_cpu_encoders() -> None:
    if not has_cpu_encoders():
        raise ToolError(
            "FFmpeg без CPU-энкодеров: libx265, libsvtav1. "
            "Установите полную сборку FFmpeg или используйте --encoder gpu."
        )


def resolve_encoder_backend(
    requested: EncoderBackend,
    *,
    encoders: set[str] | None = None,
) -> tuple[EncoderBackend, str]:
    """Return (GPU|CPU, human note). Never returns AUTO."""
    names = encoders if encoders is not None else list_ffmpeg_encoders()
    nvenc = has_nvenc(names)
    cpu = has_cpu_encoders(names)

    if requested is EncoderBackend.GPU:
        if not nvenc:
            raise ToolError(
                "Encoder=gpu, но NVENC недоступен (нужны hevc_nvenc и av1_nvenc). "
                "Попробуйте --encoder auto или --encoder cpu."
            )
        return EncoderBackend.GPU, "encoder: gpu (NVENC)"

    if requested is EncoderBackend.CPU:
        if not cpu:
            raise ToolError(
                "Encoder=cpu, но libx265/libsvtav1 недоступны в FFmpeg."
            )
        return EncoderBackend.CPU, "encoder: cpu (libx265 / libsvtav1)"

    if requested is EncoderBackend.AUTO:
        if nvenc:
            return EncoderBackend.GPU, "encoder: gpu (auto — NVENC available)"
        if cpu:
            return (
                EncoderBackend.CPU,
                "encoder: cpu (auto-fallback — NVENC unavailable)",
            )
        raise ToolError(
            "Encoder=auto: нет ни NVENC (hevc_nvenc/av1_nvenc), "
            "ни CPU (libx265/libsvtav1)."
        )

    raise AssertionError(f"Unhandled encoder backend: {requested}")


def validate_environment(
    encoder: EncoderBackend = EncoderBackend.GPU,
) -> list[str]:
    """Raise ToolError if unusable; otherwise return human-readable OK lines."""
    require_tools()
    names = list_ffmpeg_encoders()
    resolved, note = resolve_encoder_backend(encoder, encoders=names)
    lines = [*describe_tools(), note]
    if resolved is EncoderBackend.GPU:
        lines.append("encoders: hevc_nvenc, av1_nvenc")
    else:
        lines.append("encoders: libx265, libsvtav1")
    return lines


def probe_media(path: Path) -> MediaInfo:
    require_tools()
    cmd = [
        ffprobe_executable(),
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ToolError(f"ffprobe не смог прочитать файл: {path}\n{result.stderr}")

    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    fmt = data.get("format") or {}

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration") or (video or {}).get("duration") or 0)
    size = int(fmt.get("size") or path.stat().st_size)

    return MediaInfo(
        path=str(path),
        size_bytes=size,
        duration_sec=duration,
        video_codec=(video or {}).get("codec_name"),
        width=int(video["width"]) if video and video.get("width") else None,
        height=int(video["height"]) if video and video.get("height") else None,
        has_audio=audio is not None,
    )
