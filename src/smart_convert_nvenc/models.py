from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class VideoCodec(str, Enum):
    HEVC = "hevc"
    AV1 = "av1"


class EncoderBackend(str, Enum):
    """Requested or resolved video encode backend."""

    GPU = "gpu"
    CPU = "cpu"
    AUTO = "auto"


# ffprobe codec_name values that count as already-encoded targets
_HEVC_PROBE_NAMES = frozenset({"hevc", "h265", "hev1", "hvc1"})
_AV1_PROBE_NAMES = frozenset({"av1", "av01"})


def normalize_probe_codec(name: str | None) -> str | None:
    if not name:
        return None
    return name.strip().lower()


def probe_codec_is(name: str | None, codec: VideoCodec) -> bool:
    normalized = normalize_probe_codec(name)
    if normalized is None:
        return False
    if codec is VideoCodec.HEVC:
        return normalized in _HEVC_PROBE_NAMES
    if codec is VideoCodec.AV1:
        return normalized in _AV1_PROBE_NAMES
    raise AssertionError(f"Unhandled codec: {codec}")


def already_target_codec(
    probe_name: str | None,
    *,
    force: VideoCodec | None = None,
) -> VideoCodec | None:
    """If source is already a codec we would keep, return that codec; else None.

    - force set → skip only when source matches that codec
    - auto → skip when source is already HEVC or AV1
    """
    if force is not None:
        return force if probe_codec_is(probe_name, force) else None
    if probe_codec_is(probe_name, VideoCodec.HEVC):
        return VideoCodec.HEVC
    if probe_codec_is(probe_name, VideoCodec.AV1):
        return VideoCodec.AV1
    return None


class AudioMode(str, Enum):
    COPY = "copy"
    AAC = "aac"
    OPUS = "opus"


@dataclass(frozen=True)
class AudioSettings:
    mode: AudioMode = AudioMode.COPY
    bitrate_k: int = 128

    @classmethod
    def parse(cls, value: str) -> AudioSettings:
        raw = value.strip().lower()
        if raw in {"copy", "c"}:
            return cls(mode=AudioMode.COPY)
        if ":" in raw:
            name, rate = raw.split(":", 1)
            bitrate = int(rate.rstrip("k"))
        else:
            name, bitrate = raw, 128
        if name == "aac":
            return cls(mode=AudioMode.AAC, bitrate_k=bitrate)
        if name == "opus":
            return cls(mode=AudioMode.OPUS, bitrate_k=bitrate)
        raise ValueError(
            f"Unknown audio mode '{value}'. Use: copy | aac[:bitrate] | opus[:bitrate]"
        )


@dataclass(frozen=True)
class EncodeProfile:
    codec: VideoCodec
    cq: int
    preset: str = "p6"
    container_ext: str = ".mp4"
    backend: EncoderBackend = EncoderBackend.GPU

    @property
    def nvenc_name(self) -> str:
        if self.codec is VideoCodec.HEVC:
            return "hevc_nvenc"
        if self.codec is VideoCodec.AV1:
            return "av1_nvenc"
        raise AssertionError(f"Unhandled codec: {self.codec}")

    @property
    def cpu_encoder_name(self) -> str:
        if self.codec is VideoCodec.HEVC:
            return "libx265"
        if self.codec is VideoCodec.AV1:
            return "libsvtav1"
        raise AssertionError(f"Unhandled codec: {self.codec}")


@dataclass(frozen=True)
class ConvertSettings:
    sample_seconds: float = 30.0
    sample_offset_ratio: float = 0.25
    min_savings: float = 0.10
    hevc_cq: int = 28
    av1_cq: int = 32
    preset: str = "p6"
    audio: AudioSettings = AudioSettings()
    dry_run: bool = False
    force_codec: VideoCodec | None = None
    keep_samples: bool = False
    skip_same_codec: bool = True
    encoder: EncoderBackend = EncoderBackend.GPU

    def hevc_profile(self, *, backend: EncoderBackend = EncoderBackend.GPU) -> EncodeProfile:
        if backend is EncoderBackend.AUTO:
            raise ValueError("EncodeProfile backend must be resolved GPU or CPU, not AUTO")
        return EncodeProfile(
            codec=VideoCodec.HEVC,
            cq=self.hevc_cq,
            preset=self.preset,
            container_ext=".mp4",
            backend=backend,
        )

    def av1_profile(self, *, backend: EncoderBackend = EncoderBackend.GPU) -> EncodeProfile:
        if backend is EncoderBackend.AUTO:
            raise ValueError("EncodeProfile backend must be resolved GPU or CPU, not AUTO")
        return EncodeProfile(
            codec=VideoCodec.AV1,
            cq=self.av1_cq,
            preset=self.preset,
            container_ext=".mkv",
            backend=backend,
        )


@dataclass(frozen=True)
class MediaInfo:
    path: str
    size_bytes: int
    duration_sec: float
    video_codec: str | None
    width: int | None
    height: int | None
    has_audio: bool


@dataclass(frozen=True)
class SampleResult:
    profile: EncodeProfile
    path: str
    size_bytes: int
    elapsed_sec: float


@dataclass(frozen=True)
class BenchmarkReport:
    winner: EncodeProfile
    hevc: SampleResult | None
    av1: SampleResult | None
    projected_full_bytes: int
    original_bytes: int
    savings_ratio: float
    worth_encoding: bool
    disclaimer: str


@dataclass(frozen=True)
class VideoDecision:
    source: Path
    original_size: int
    compressed: bool
    output: Path
    profile: EncodeProfile | None
    projected_or_final_size: int


DISCLAIMER_SIZE_AT_CQ = (
    "Сравнение по размеру при разных CQ (HEVC vs AV1) — не равное качество. "
    "Для курсов этого обычно достаточно; VMAF в MVP не используется."
)

VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".webm",
    ".flv",
    ".mpg",
    ".mpeg",
    ".ts",
    ".mts",
}

_JUNK_FILE_NAMES = frozenset({"thumbs.db", "desktop.ini", ".ds_store"})


def is_video_media(path: Path) -> bool:
    """True for real video files we may encode (skips AppleDouble ``._*`` and similar junk)."""
    name = path.name
    if name.startswith("._") or name.startswith("."):
        return False
    if name.casefold() in _JUNK_FILE_NAMES:
        return False
    return path.suffix.lower() in VIDEO_EXTENSIONS
