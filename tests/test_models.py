from __future__ import annotations

from pathlib import Path

import pytest

from smart_convert_nvenc.models import (
    AudioMode,
    AudioSettings,
    ConvertSettings,
    EncoderBackend,
    EncodeProfile,
    VideoCodec,
    already_target_codec,
    is_video_media,
    probe_codec_is,
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
    assert hevc.backend is EncoderBackend.GPU
    assert av1.codec is VideoCodec.AV1
    assert av1.cq == settings.av1_cq
    assert av1.container_ext == ".mkv"
    assert av1.backend is EncoderBackend.GPU
    assert settings.skip_same_codec is True
    assert settings.encoder is EncoderBackend.GPU
    cpu = settings.hevc_profile(backend=EncoderBackend.CPU)
    assert cpu.backend is EncoderBackend.CPU
    assert cpu.cpu_encoder_name == "libx265"
    with pytest.raises(ValueError, match="AUTO"):
        settings.hevc_profile(backend=EncoderBackend.AUTO)


def test_probe_codec_helpers() -> None:
    assert probe_codec_is("hevc", VideoCodec.HEVC)
    assert probe_codec_is("hvc1", VideoCodec.HEVC)
    assert probe_codec_is("av01", VideoCodec.AV1)
    assert not probe_codec_is("h264", VideoCodec.HEVC)
    assert already_target_codec("h264") is None
    assert already_target_codec("hevc") is VideoCodec.HEVC
    assert already_target_codec("av1") is VideoCodec.AV1
    assert already_target_codec("hevc", force=VideoCodec.AV1) is None
    assert already_target_codec("hevc", force=VideoCodec.HEVC) is VideoCodec.HEVC


def test_is_video_media_skips_appledouble(tmp_path: Path) -> None:
    real = tmp_path / "lesson.mp4"
    junk = tmp_path / "._lesson.mp4"
    real.write_bytes(b"x")
    junk.write_bytes(b"y")
    assert is_video_media(real)
    assert not is_video_media(junk)
    assert not is_video_media(tmp_path / ".hidden.mp4")
    assert not is_video_media(tmp_path / "Thumbs.db")
