from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .models import MediaInfo


class ToolError(RuntimeError):
    pass


def require_tools() -> None:
    for name in ("ffmpeg", "ffprobe"):
        if shutil.which(name) is None:
            raise ToolError(f"Не найден `{name}` в PATH. Установите FFmpeg (например gyan.dev).")


def require_nvenc() -> None:
    require_tools()
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = (result.stdout or "") + (result.stderr or "")
    missing = [name for name in ("hevc_nvenc", "av1_nvenc") if name not in text]
    if missing:
        raise ToolError(
            "FFmpeg без нужных NVENC-энкодеров: "
            + ", ".join(missing)
            + ". Нужна сборка с NVENC и GPU RTX 40xx (для AV1 encode)."
        )


def probe_media(path: Path) -> MediaInfo:
    require_tools()
    cmd = [
        "ffprobe",
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
