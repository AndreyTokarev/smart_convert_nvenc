from __future__ import annotations

from pathlib import Path

import pytest

from smart_convert_nvenc.models import AudioMode, EncoderBackend
from smart_convert_nvenc.profiles import get_profile, list_profile_names, load_profiles_toml


def test_bundled_profiles_include_default_and_course() -> None:
    names = list_profile_names()
    assert names == ["course", "default"]


def test_default_profile_matches_legacy_defaults() -> None:
    profile = get_profile("default")
    settings = profile.to_convert_settings()
    assert settings.sample_seconds == 30.0
    assert settings.hevc_cq == 28
    assert settings.av1_cq == 32
    assert settings.preset == "p6"
    assert settings.audio.mode is AudioMode.COPY
    assert settings.encoder is EncoderBackend.GPU


def test_course_profile_is_more_aggressive() -> None:
    profile = get_profile("course")
    settings = profile.to_convert_settings()
    assert settings.sample_seconds == 20.0
    assert settings.hevc_cq == 32
    assert settings.av1_cq == 36
    assert settings.audio.mode is AudioMode.OPUS
    assert settings.audio.bitrate_k == 96
    assert profile.min_course_savings == 0.10


def test_cli_overrides_profile_values() -> None:
    profile = get_profile("default")
    settings = profile.to_convert_settings(hevc_cq=40, audio="aac:64", encoder="cpu")
    assert settings.hevc_cq == 40
    assert settings.av1_cq == 32
    assert settings.audio.mode is AudioMode.AAC
    assert settings.audio.bitrate_k == 64
    assert settings.encoder is EncoderBackend.CPU


def test_unknown_profile() -> None:
    with pytest.raises(ValueError, match="Unknown profile"):
        get_profile("nope")


def test_load_profiles_from_path(tmp_path: Path) -> None:
    path = tmp_path / "profiles.toml"
    path.write_text(
        """
[tiny]
description = "test"
sample_seconds = 5
sample_offset_ratio = 0.1
min_savings = 0.05
hevc_cq = 20
av1_cq = 22
preset = "p4"
audio = "copy"
encoder = "auto"
""",
        encoding="utf-8",
    )
    profile = get_profile("tiny", path=path)
    assert profile.hevc_cq == 20
    assert profile.encoder == "auto"


def test_missing_required_key() -> None:
    with pytest.raises(ValueError, match="missing required key"):
        load_profiles_toml("[broken]\nhevc_cq = 1\n")
