from __future__ import annotations

from unittest.mock import patch

from smart_convert_nvenc.launcher import main


def test_launcher_help() -> None:
    assert main(["--help"]) == 0
    assert main(["help"]) == 0


def test_launcher_dispatches_course() -> None:
    with patch("smart_convert_nvenc.course_cli.main", return_value=0) as course:
        assert main(["course", "--dry-run"]) == 0
        course.assert_called_once_with(["--dry-run"])


def test_launcher_dispatches_cli() -> None:
    with patch("smart_convert_nvenc.cli.main", return_value=0) as cli:
        assert main(["video.mp4", "--dry-run"]) == 0
        cli.assert_called_once_with(["video.mp4", "--dry-run"])


def test_launcher_dispatches_gui() -> None:
    with patch("smart_convert_nvenc.gui.main", return_value=0) as gui:
        assert main([]) == 0
        gui.assert_called_once_with()
    with patch("smart_convert_nvenc.gui.main", return_value=0) as gui:
        assert main(["gui"]) == 0
        gui.assert_called_once_with()
