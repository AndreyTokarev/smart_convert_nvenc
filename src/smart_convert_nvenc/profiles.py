from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from .models import AudioSettings, ConvertSettings, EncoderBackend, VideoCodec, VmafMode

_PROFILES_RESOURCE = files("smart_convert_nvenc.data").joinpath("profiles.toml")


@dataclass(frozen=True)
class NamedProfile:
    name: str
    description: str
    sample_seconds: float
    sample_offset_ratio: float
    min_savings: float
    min_course_savings: float
    hevc_cq: int
    av1_cq: int
    preset: str
    audio: str
    encoder: str
    vmaf: str
    vmaf_min: float

    def to_convert_settings(
        self,
        *,
        sample_seconds: float | None = None,
        sample_offset_ratio: float | None = None,
        min_savings: float | None = None,
        hevc_cq: int | None = None,
        av1_cq: int | None = None,
        preset: str | None = None,
        audio: str | None = None,
        encoder: str | None = None,
        vmaf: str | None = None,
        vmaf_min: float | None = None,
        dry_run: bool = False,
        force_codec: VideoCodec | None = None,
        keep_samples: bool = False,
        skip_same_codec: bool = True,
    ) -> ConvertSettings:
        enc_raw = encoder if encoder is not None else self.encoder
        audio_raw = audio if audio is not None else self.audio
        vmaf_raw = vmaf if vmaf is not None else self.vmaf
        return ConvertSettings(
            sample_seconds=self.sample_seconds if sample_seconds is None else sample_seconds,
            sample_offset_ratio=(
                self.sample_offset_ratio if sample_offset_ratio is None else sample_offset_ratio
            ),
            min_savings=self.min_savings if min_savings is None else min_savings,
            hevc_cq=self.hevc_cq if hevc_cq is None else hevc_cq,
            av1_cq=self.av1_cq if av1_cq is None else av1_cq,
            preset=self.preset if preset is None else preset,
            audio=AudioSettings.parse(audio_raw),
            dry_run=dry_run,
            force_codec=force_codec,
            keep_samples=keep_samples,
            skip_same_codec=skip_same_codec,
            encoder=EncoderBackend(enc_raw),
            vmaf=VmafMode(vmaf_raw),
            vmaf_min=self.vmaf_min if vmaf_min is None else vmaf_min,
        )


def _parse_profile(name: str, raw: dict[str, Any]) -> NamedProfile:
    try:
        return NamedProfile(
            name=name,
            description=str(raw.get("description", "")),
            sample_seconds=float(raw["sample_seconds"]),
            sample_offset_ratio=float(raw["sample_offset_ratio"]),
            min_savings=float(raw["min_savings"]),
            min_course_savings=float(raw.get("min_course_savings", raw["min_savings"])),
            hevc_cq=int(raw["hevc_cq"]),
            av1_cq=int(raw["av1_cq"]),
            preset=str(raw["preset"]),
            audio=str(raw["audio"]),
            encoder=str(raw["encoder"]),
            vmaf=str(raw.get("vmaf", "auto")),
            vmaf_min=float(raw.get("vmaf_min", 90.0)),
        )
    except KeyError as exc:
        raise ValueError(f"Profile '{name}' missing required key: {exc.args[0]}") from exc


def load_profiles_toml(text: str) -> dict[str, NamedProfile]:
    data = tomllib.loads(text)
    if not data:
        raise ValueError("profiles.toml is empty")
    return {name: _parse_profile(name, section) for name, section in data.items()}


def load_profiles(*, path: Path | None = None) -> dict[str, NamedProfile]:
    if path is not None:
        text = path.read_text(encoding="utf-8")
    else:
        text = _PROFILES_RESOURCE.read_text(encoding="utf-8")
    return load_profiles_toml(text)


def list_profile_names(*, path: Path | None = None) -> list[str]:
    return sorted(load_profiles(path=path))


def get_profile(name: str, *, path: Path | None = None) -> NamedProfile:
    profiles = load_profiles(path=path)
    try:
        return profiles[name]
    except KeyError as exc:
        known = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown profile '{name}'. Known: {known}") from exc
