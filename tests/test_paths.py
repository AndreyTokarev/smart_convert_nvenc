from __future__ import annotations

import sys
from pathlib import Path

import pytest

from smart_convert_nvenc.paths import (
    CoursePaths,
    ensure_long_paths,
    find_project_root,
    fs_path,
    long_paths_enabled,
    resolve_course_paths,
    try_enable_long_paths,
)


def test_find_project_root() -> None:
    root = find_project_root()
    assert (root / "pyproject.toml").is_file()


def test_find_project_root_from_start(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert find_project_root(nested) == tmp_path.resolve()


def test_find_project_root_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Point module __file__ into the empty temp tree so real repo is not discovered.
    monkeypatch.setattr(
        "smart_convert_nvenc.paths.__file__",
        str(tmp_path / "fake_paths.py"),
    )
    with pytest.raises(RuntimeError, match="pyproject.toml"):
        find_project_root(tmp_path)


def test_find_project_root_skips_seen(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    # Calling with start equal to a parent that will also appear via cwd/__file__ still works.
    assert find_project_root(tmp_path) == tmp_path.resolve()


def test_resolve_defaults_under_project() -> None:
    root = find_project_root()
    paths = resolve_course_paths(project_root=root)
    assert paths.inbox == (root / "courses" / "inbox").resolve()
    assert paths.outbox == (root / "courses" / "outbox").resolve()
    assert paths.tmp == (root / "courses" / "tmp").resolve()


def test_resolve_all_explicit_skips_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "smart_convert_nvenc.paths.__file__",
        str(tmp_path / "fake_paths.py"),
    )
    monkeypatch.chdir(tmp_path)
    paths = resolve_course_paths(
        inbox=tmp_path / "i",
        outbox=tmp_path / "o",
        tmp=tmp_path / "t",
    )
    assert paths.inbox == (tmp_path / "i").resolve()


def test_default_data_root_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_exe = tmp_path / "bundle" / "smart-convert-gui.exe"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.write_bytes(b"x")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    from smart_convert_nvenc.paths import default_data_root

    assert default_data_root() == fake_exe.parent.resolve()
    paths = resolve_course_paths()
    assert paths.inbox == (fake_exe.parent / "courses" / "inbox").resolve()


def test_resolve_cli_overrides(tmp_path: Path) -> None:
    paths = resolve_course_paths(
        project_root=tmp_path,
        inbox=tmp_path / "i",
        outbox=tmp_path / "o",
        tmp=tmp_path / "t",
    )
    assert paths.inbox == (tmp_path / "i").resolve()
    assert paths.outbox == (tmp_path / "o").resolve()
    assert paths.tmp == (tmp_path / "t").resolve()


def test_resolve_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMART_CONVERT_COURSES_ROOT", str(tmp_path / "croot"))
    monkeypatch.setenv("SMART_CONVERT_INBOX", str(tmp_path / "ein"))
    monkeypatch.setenv("SMART_CONVERT_OUTBOX", str(tmp_path / "eout"))
    monkeypatch.setenv("SMART_CONVERT_TMP", str(tmp_path / "etmp"))
    paths = resolve_course_paths(project_root=tmp_path)
    assert paths.inbox == (tmp_path / "ein").resolve()
    assert paths.outbox == (tmp_path / "eout").resolve()
    assert paths.tmp == (tmp_path / "etmp").resolve()


def test_resolve_courses_root_env_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "SMART_CONVERT_COURSES_ROOT",
        "SMART_CONVERT_INBOX",
        "SMART_CONVERT_OUTBOX",
        "SMART_CONVERT_TMP",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SMART_CONVERT_COURSES_ROOT", str(tmp_path / "bundle"))
    paths = resolve_course_paths(project_root=tmp_path)
    assert paths.inbox == (tmp_path / "bundle" / "inbox").resolve()


def test_course_paths_ensure(tmp_path: Path) -> None:
    paths = CoursePaths(
        inbox=tmp_path / "inbox",
        outbox=tmp_path / "outbox",
        tmp=tmp_path / "tmp",
    )
    paths.ensure()
    assert paths.inbox.is_dir()
    assert paths.outbox.is_dir()
    assert paths.tmp.is_dir()


def test_fs_path_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    p = tmp_path / "a.mp4"
    assert fs_path(p) == str(p)


def test_fs_path_adds_extended_prefix_when_long(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "smart_convert_nvenc.paths.long_paths_enabled",
        lambda: False,
    )
    long_name = "x" * 250 + ".mp4"
    p = tmp_path / long_name
    text = fs_path(p)
    assert text.startswith("\\\\?\\")
    assert text.endswith(long_name)


def test_fs_path_short_when_long_paths_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "smart_convert_nvenc.paths.long_paths_enabled",
        lambda: True,
    )
    p = tmp_path / "short.mp4"
    p.write_bytes(b"x")
    assert not fs_path(p).startswith("\\\\?\\")


def test_ensure_long_paths_noop_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert ensure_long_paths() is True


def test_try_enable_when_already_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        "smart_convert_nvenc.paths.long_paths_enabled",
        lambda: True,
    )
    assert try_enable_long_paths() is True


def test_long_paths_enabled_reads_registry_shape() -> None:
    # On this CI/dev Windows box the helper must not crash.
    value = long_paths_enabled()
    assert value is None or isinstance(value, bool)
