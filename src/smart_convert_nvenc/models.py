from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VideoCodec(str, Enum):
    HEVC = "hevc"
    AV1 = "av1"


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

    @property
    def nvenc_name(self) -> str:
        if self.codec is VideoCodec.HEVC:
            return "hevc_nvenc"
        if self.codec is VideoCodec.AV1:
            return "av1_nvenc"
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

    def hevc_profile(self) -> EncodeProfile:
        return EncodeProfile(
            codec=VideoCodec.HEVC,
            cq=self.hevc_cq,
            preset=self.preset,
            container_ext=".mp4",
        )

    def av1_profile(self) -> EncodeProfile:
        return EncodeProfile(
            codec=VideoCodec.AV1,
            cq=self.av1_cq,
            preset=self.preset,
            container_ext=".mkv",
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
    hevc: SampleResult
    av1: SampleResult
    projected_full_bytes: int
    original_bytes: int
    savings_ratio: float
    worth_encoding: bool
    disclaimer: str


DISCLAIMER_SIZE_AT_CQ = (
    "Сравнение по размеру при разных CQ (HEVC vs AV1) — не равное качество. "
    "Для курсов этого обычно достаточно; VMAF в MVP не используется."
)
