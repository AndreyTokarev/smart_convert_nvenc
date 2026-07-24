from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_convert_nvenc import cli, course_cli
from smart_convert_nvenc.probe import ToolError


def test_cli_build_parser() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        ["video.mp4", "--force-codec", "hevc", "--dry-run", "--encoder", "auto"]
    )
    assert args.force_codec == "hevc"
    assert args.dry_run is True
    assert args.encoder == "auto"


def test_course_cli_build_parser_encoder() -> None:
    parser = course_cli.build_parser()
    args = parser.parse_args(["--encoder", "cpu"])
    assert args.encoder == "cpu"

def test_cli_main_success(tmp_path: Path) -> None:
    video = tmp_path / "a.mp4"
    video.write_bytes(b"x")
    with (
        patch("smart_convert_nvenc.cli.validate_environment", return_value=["ok"]),
        patch("smart_convert_nvenc.cli.convert_one", return_value=video) as convert,
    ):
        assert cli.main([str(video), "--audio", "copy"]) == 0
        convert.assert_called_once()


def test_cli_main_error() -> None:
    with patch(
        "smart_convert_nvenc.cli.validate_environment",
        side_effect=ToolError("no ffmpeg"),
    ):
        assert cli.main(["missing.mp4"]) == 1


def test_cli_safe_print_unicode(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    state = {"n": 0}

    def _print(msg: object = "", *args: object, **kwargs: object) -> None:
        state["n"] += 1
        if state["n"] == 1:
            raise UnicodeEncodeError("ascii", "x", 0, 1, "no")
        calls.append(str(msg))

    monkeypatch.setattr(cli.sys, "stdout", MagicMock(encoding="ascii"))
    monkeypatch.setattr("builtins.print", _print)
    cli._safe_print("ok")
    assert calls


def test_course_cli_empty_inbox(tmp_path: Path) -> None:
    with (
        patch(
            "smart_convert_nvenc.course_cli.resolve_course_paths",
            return_value=MagicMock(
                inbox=tmp_path / "inbox",
                outbox=tmp_path / "outbox",
                tmp=tmp_path / "tmp",
                ensure=MagicMock(),
            ),
        ),
        patch("smart_convert_nvenc.course_cli.validate_environment", return_value=[]),
        patch("smart_convert_nvenc.course_cli.cleanup_conversion_temps", return_value=[]),
        patch("smart_convert_nvenc.course_cli.list_course_dirs", return_value=[]),
        patch("smart_convert_nvenc.course_cli.WindowsSessionGuard") as guard_cls,
    ):
        guard = guard_cls.return_value
        code = course_cli.main([])
    assert code == 0
    guard.start.assert_not_called()


def test_course_cli_runs_named_course(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    course = inbox / "C1"
    course.mkdir(parents=True)
    paths = MagicMock()
    paths.inbox = inbox
    paths.outbox = tmp_path / "outbox"
    paths.tmp = tmp_path / "tmp"
    paths.ensure = MagicMock()

    with (
        patch("smart_convert_nvenc.course_cli.resolve_course_paths", return_value=paths),
        patch("smart_convert_nvenc.course_cli.validate_environment", return_value=["env"]),
        patch("smart_convert_nvenc.course_cli.cleanup_conversion_temps", return_value=[Path("x")]),
        patch("smart_convert_nvenc.course_cli.convert_course") as convert,
        patch("smart_convert_nvenc.course_cli.WindowsSessionGuard") as guard_cls,
    ):
        guard = guard_cls.return_value
        code = course_cli.main(["C1", "--force-codec", "av1"])
    assert code == 0
    convert.assert_called_once()
    guard.start.assert_called_once()
    guard.stop.assert_called_once()


def test_course_cli_safe_print_unicode(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    state = {"n": 0}

    def _print(msg: object = "", *args: object, **kwargs: object) -> None:
        state["n"] += 1
        if state["n"] == 1:
            raise UnicodeEncodeError("ascii", "x", 0, 1, "no")
        calls.append(str(msg))

    monkeypatch.setattr(course_cli.sys, "stdout", MagicMock(encoding="ascii"))
    monkeypatch.setattr("builtins.print", _print)
    course_cli._safe_print("ok")
    assert calls


def test_course_cli_missing_course(tmp_path: Path) -> None:
    paths = MagicMock()
    paths.inbox = tmp_path / "inbox"
    paths.inbox.mkdir()
    paths.outbox = tmp_path / "outbox"
    paths.tmp = tmp_path / "tmp"
    paths.ensure = MagicMock()
    with (
        patch("smart_convert_nvenc.course_cli.resolve_course_paths", return_value=paths),
        patch("smart_convert_nvenc.course_cli.validate_environment", return_value=[]),
        patch("smart_convert_nvenc.course_cli.cleanup_conversion_temps", return_value=[]),
    ):
        assert course_cli.main(["NoSuch"]) == 1
