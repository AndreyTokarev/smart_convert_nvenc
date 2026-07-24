from __future__ import annotations

import re

import pytest

from smart_convert_nvenc import __version__, cli, course_cli


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_cli_version_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["--version"])
    assert exc.value.code == 0


def test_course_cli_version_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        course_cli.build_parser().parse_args(["--version"])
    assert exc.value.code == 0
