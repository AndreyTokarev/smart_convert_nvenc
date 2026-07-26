from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_convert_nvenc.ffmpeg_tools import resolve_tool
from smart_convert_nvenc.models import EncoderBackend
from smart_convert_nvenc.probe import (
    ToolError,
    has_cpu_encoders,
    has_nvenc,
    probe_media,
    require_nvenc,
    require_tools,
    resolve_encoder_backend,
    validate_environment,
)


def test_require_tools_missing() -> None:
    with patch(
        "smart_convert_nvenc.probe.resolve_tool",
        side_effect=FileNotFoundError("ffmpeg"),
    ):
        with pytest.raises(ToolError, match="ffmpeg"):
            require_tools()


def test_require_nvenc_ok() -> None:
    result = MagicMock()
    result.stdout = " V..... hevc_nvenc\n V..... av1_nvenc\n"
    result.stderr = ""
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        require_nvenc()


def test_require_nvenc_missing() -> None:
    result = MagicMock()
    result.stdout = " V..... libx264\n"
    result.stderr = ""
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.ffmpeg_executable", return_value="ffmpeg"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        with pytest.raises(ToolError, match="hevc_nvenc"):
            require_nvenc()


def test_resolve_encoder_auto_fallback_to_cpu() -> None:
    names = {"libx265", "libsvtav1", "libx264"}
    assert has_nvenc(names) is False
    assert has_cpu_encoders(names) is True
    backend, note = resolve_encoder_backend(EncoderBackend.AUTO, encoders=names)
    assert backend is EncoderBackend.CPU
    assert "auto-fallback" in note


def test_resolve_encoder_gpu_when_nvenc_present() -> None:
    names = {"hevc_nvenc", "av1_nvenc", "libx265", "libsvtav1"}
    backend, note = resolve_encoder_backend(EncoderBackend.AUTO, encoders=names)
    assert backend is EncoderBackend.GPU
    assert "NVENC" in note


def test_resolve_encoder_cpu_requires_libs() -> None:
    with pytest.raises(ToolError, match="libx265"):
        resolve_encoder_backend(EncoderBackend.CPU, encoders={"hevc_nvenc", "av1_nvenc"})


def test_resolve_encoder_gpu_with_av1_nvenc() -> None:
    backend, note = resolve_encoder_backend(
        EncoderBackend.GPU,
        encoders={"hevc_nvenc", "av1_nvenc"},
    )
    assert backend is EncoderBackend.GPU
    assert "av1" in note


def test_resolve_encoder_gpu_hevc_only_no_cpu() -> None:
    backend, note = resolve_encoder_backend(
        EncoderBackend.GPU,
        encoders={"hevc_nvenc"},
    )
    assert backend is EncoderBackend.GPU
    assert "AV1 unavailable" in note


def test_resolve_encoder_auto_with_hevc_and_svt() -> None:
    backend, note = resolve_encoder_backend(
        EncoderBackend.AUTO,
        encoders={"hevc_nvenc", "libx265", "libsvtav1"},
    )
    assert backend is EncoderBackend.GPU
    assert "libsvtav1" in note


def test_validate_environment_lists_svt_fallback() -> None:
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch(
            "smart_convert_nvenc.probe.list_ffmpeg_encoders",
            return_value={"hevc_nvenc", "libx265", "libsvtav1"},
        ),
        patch(
            "smart_convert_nvenc.probe.describe_tools",
            return_value=["ffmpeg: x (path)", "ffprobe: y (path)"],
        ),
    ):
        lines = validate_environment(EncoderBackend.GPU)
    assert any("libsvtav1" in line for line in lines)


def test_resolve_encoder_cpu_ok() -> None:
    backend, note = resolve_encoder_backend(
        EncoderBackend.CPU,
        encoders={"libx265", "libsvtav1"},
    )
    assert backend is EncoderBackend.CPU
    assert "libx265" in note


def test_resolve_encoder_auto_neither() -> None:
    with pytest.raises(ToolError):
        resolve_encoder_backend(EncoderBackend.AUTO, encoders={"libx264"})


def test_require_cpu_encoders_missing() -> None:
    from smart_convert_nvenc.probe import require_cpu_encoders

    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.list_ffmpeg_encoders", return_value=set()),
    ):
        with pytest.raises(ToolError, match="libx265"):
            require_cpu_encoders()


def test_validate_environment_cpu() -> None:
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.list_ffmpeg_encoders", return_value=set()),
        patch(
            "smart_convert_nvenc.probe.resolve_encoder_backend",
            return_value=(EncoderBackend.CPU, "encoder: cpu"),
        ),
        patch(
            "smart_convert_nvenc.probe.describe_tools",
            return_value=["ffmpeg: /x (path)", "ffprobe: /y (path)"],
        ),
    ):
        lines = validate_environment(EncoderBackend.CPU)
    assert any("libx265" in line for line in lines)


def test_validate_environment() -> None:
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.list_ffmpeg_encoders", return_value=set()),
        patch(
            "smart_convert_nvenc.probe.resolve_encoder_backend",
            return_value=(EncoderBackend.GPU, "encoder: gpu (NVENC)"),
        ),
        patch(
            "smart_convert_nvenc.probe.describe_tools",
            return_value=["ffmpeg: /bin/ffmpeg (path)", "ffprobe: /bin/ffprobe (path)"],
        ),
    ):
        lines = validate_environment(EncoderBackend.GPU)
    assert any("ffmpeg" in line for line in lines)
    assert any("encoder: gpu" in line for line in lines)


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
        patch("smart_convert_nvenc.probe.ffprobe_executable", return_value="ffprobe"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        info = probe_media(path)
    assert info.duration_sec == 12.5
    assert info.size_bytes == 5
    assert info.video_codec == "h264"
    assert info.width == 1280
    assert info.height == 720
    assert info.has_audio is True
    assert info.audio_codec == "aac"

    path = tmp_path / "bad.mp4"
    path.write_bytes(b"x")
    result = MagicMock()
    result.returncode = 1
    result.stdout = ""
    result.stderr = "boom"
    with (
        patch("smart_convert_nvenc.probe.require_tools"),
        patch("smart_convert_nvenc.probe.ffprobe_executable", return_value="ffprobe"),
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
        patch("smart_convert_nvenc.probe.ffprobe_executable", return_value="ffprobe"),
        patch("smart_convert_nvenc.probe.subprocess.run", return_value=result),
    ):
        info = probe_media(path)
    assert info.video_codec is None
    assert info.width is None
    assert info.has_audio is False


def _touch_tool(bin_dir: Path, name: str) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    path = bin_dir / f"{name}{suffix}"
    path.write_bytes(b"x")
    return path


def test_resolve_tool_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "custom"
    bin_dir.mkdir()
    ffmpeg = _touch_tool(bin_dir, "ffmpeg")
    _touch_tool(bin_dir, "ffprobe")
    monkeypatch.setenv("SMART_CONVERT_FFMPEG_DIR", str(bin_dir))
    monkeypatch.delenv("PATH", raising=False)
    path, source = resolve_tool("ffmpeg")
    assert Path(path) == ffmpeg.resolve()
    assert source == "env"


def test_resolve_tool_bundled_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_exe = tmp_path / "app" / "smart-convert-gui.exe"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.write_bytes(b"x")
    bin_dir = fake_exe.parent / "ffmpeg" / "bin"
    bin_dir.mkdir(parents=True)
    bundled = _touch_tool(bin_dir, "ffmpeg")
    _touch_tool(bin_dir, "ffprobe")
    monkeypatch.delenv("SMART_CONVERT_FFMPEG_DIR", raising=False)
    monkeypatch.setattr("smart_convert_nvenc.ffmpeg_tools.is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    path, source = resolve_tool("ffmpeg")
    assert Path(path) == bundled.resolve()
    assert source == "bundled"


def test_resolve_tool_env_bin_subdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "ffmpeg"
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    ffmpeg = _touch_tool(bin_dir, "ffmpeg")
    _touch_tool(bin_dir, "ffprobe")
    monkeypatch.setenv("SMART_CONVERT_FFMPEG_DIR", str(root))
    path, source = resolve_tool("ffmpeg")
    assert Path(path) == ffmpeg.resolve()
    assert source == "env"


def test_resolve_tool_unknown_name() -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        resolve_tool("ffplay")


def test_describe_and_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from smart_convert_nvenc.ffmpeg_tools import (
        describe_tools,
        ffmpeg_executable,
        ffprobe_executable,
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _touch_tool(bin_dir, "ffmpeg")
    _touch_tool(bin_dir, "ffprobe")
    monkeypatch.setenv("SMART_CONVERT_FFMPEG_DIR", str(bin_dir))
    assert "ffmpeg" in ffmpeg_executable()
    assert "ffprobe" in ffprobe_executable()
    lines = describe_tools()
    assert any("ffmpeg:" in line and "(env)" in line for line in lines)
    assert any("ffprobe:" in line for line in lines)


def test_describe_tools_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from smart_convert_nvenc.ffmpeg_tools import describe_tools

    monkeypatch.delenv("SMART_CONVERT_FFMPEG_DIR", raising=False)
    monkeypatch.setattr(
        "smart_convert_nvenc.ffmpeg_tools.find_bundled_bin_dir",
        lambda: None,
    )
    monkeypatch.setattr(
        "smart_convert_nvenc.ffmpeg_tools.shutil.which",
        lambda _name: None,
    )
    lines = describe_tools()
    assert lines == ["ffmpeg: not found", "ffprobe: not found"]
