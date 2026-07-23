from __future__ import annotations

import pytest

from smart_convert_nvenc.models import (
    AudioMode,
    AudioSettings,
    ConvertSettings,
    EncodeProfile,
    VideoCodec,
)


def test_audio_parse_copy_aliases() -> None:
    assert AudioSettings.parse("copy").mode is AudioMode.COPY
    assert AudioSettings.parse("C").mode is AudioMode.COPY


def test_audio_parse_aac_and_opus() -> None:
    aac = AudioSettings.parse("aac:96k")
    assert aac.mode is AudioMode.AAC
    assert aac.bitrate_k == 96
    opus = AudioSettings.parse("opus")
    assert opus.mode is AudioMode.OPUS
    assert opus.bitrate_k == 128


def test_audio_parse_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown audio mode"):
        AudioSettings.parse("flac")


def test_encode_profile_nvenc_names(hevc_profile: EncodeProfile, av1_profile: EncodeProfile) -> None:
    assert hevc_profile.nvenc_name == "hevc_nvenc"
    assert av1_profile.nvenc_name == "av1_nvenc"


def test_convert_settings_profiles(settings: ConvertSettings) -> None:
    hevc = settings.hevc_profile()
    av1 = settings.av1_profile()
    assert hevc.codec is VideoCodec.HEVC
    assert hevc.cq == settings.hevc_cq
    assert hevc.container_ext == ".mp4"
    assert av1.codec is VideoCodec.AV1
    assert av1.cq == settings.av1_cq
    assert av1.container_ext == ".mkv"
