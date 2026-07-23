from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_convert_nvenc.probe import ToolError, probe_media, require_nvenc, require_tools, validate_environment


def test_require_tools_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("smart_convert_nvenc.probe.shutil.which", lambda _name: None)
    with pytest.raises(ToolError, match="ffmpeg"):
        require_tools()


def test_require_nvenc_ok() -> None:
    result = MagicMock()
    result.stdout = " V..... hevc_nvenc\n V..... av1_nvenc\n"
    result.stderr = ""
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        require_nvenc()


def test_require_nvenc_missing() -> None:
    result = MagicMock()
    result.stdout = " V..... libx264\n"
    result.stderr = ""
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        with pytest.raises(ToolError, match="hevc_nvenc"):
            require_nvenc()


def test_validate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("smart_convert_nvenc.probe.shutil.which", lambda name: f"/bin/{name}")
    with patch("smart_convert_nvenc.probe.require_nvenc"):
        lines = validate_environment()
    assert any("ffmpeg" in line for line in lines)
    assert any("hevc_nvenc" in line for line in lines)


def test_probe_media_ok(tmp_path: Path) -> None:
    path = tmp_path / "a.mp4"
    path.write_bytes(b"12345")
    payload = {
        "format": {"duration": "12.5", "size": "5"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(payload)
    result.stderr = ""
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        info = probe_media(path)
    assert info.duration_sec == 12.5
    assert info.size_bytes == 5
    assert info.video_codec == "h264"
    assert info.width == 1280
    assert info.height == 720
    assert info.has_audio is True


def test_probe_media_failure(tmp_path: Path) -> None:
    path = tmp_path / "bad.mp4"
    path.write_bytes(b"x")
    result = MagicMock()
    result.returncode = 1
    result.stdout = ""
    result.stderr = "boom"
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        with pytest.raises(ToolError, match="ffprobe"):
            probe_media(path)


def test_probe_media_no_video_stream(tmp_path: Path) -> None:
    path = tmp_path / "a.mp4"
    path.write_bytes(b"123")
    payload = {"format": {"duration": "1", "size": "3"}, "streams": []}
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(payload)
    result.stderr = ""
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        info = probe_media(path)
    assert info.video_codec is None
    assert info.width is None
    assert info.has_audio is False
