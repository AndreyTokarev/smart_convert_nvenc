from __future__ import annotations

from pathlib import Path

from smart_convert_nvenc.gui_settings import (
    GuiSettings,
    default_settings_path,
    load_gui_settings,
    save_gui_settings,
)
from smart_convert_nvenc.paths import resolve_course_paths


def test_default_settings_path_uses_appdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SMART_CONVERT_APPDATA", str(tmp_path / "cfg"))
    path = default_settings_path()
    assert path == (tmp_path / "cfg" / "smart_convert_nvenc" / "settings.json").resolve()


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    defaults = resolve_course_paths(project_root=tmp_path)
    settings = GuiSettings(
        inbox=str(defaults.inbox),
        outbox=str(defaults.outbox),
        tmp=str(defaults.tmp),
        sample_sec="25",
        cq_hevc="30",
        codec="hevc",
        encoder="auto",
    )
    path = tmp_path / "settings.json"
    save_gui_settings(settings, path)
    loaded = load_gui_settings(path)
    assert loaded.inbox == str(defaults.inbox)
    assert loaded.sample_sec == "25"
    assert loaded.cq_hevc == "30"
    assert loaded.codec == "hevc"
    assert loaded.encoder == "auto"
    assert loaded.course_paths().inbox == defaults.inbox.resolve()


def test_load_missing_file_uses_project_defaults(tmp_path: Path) -> None:
    loaded = load_gui_settings(tmp_path / "missing.json")
    assert loaded.inbox
    assert Path(loaded.inbox).name == "inbox"


def test_load_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1,2,3]\n", encoding="utf-8")
    loaded = load_gui_settings(path)
    assert loaded.inbox


def test_load_schema_string_and_partial_paths(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        '{"schema":"1","inbox":"","outbox":"","tmp":"","codec":"av1"}\n',
        encoding="utf-8",
    )
    loaded = load_gui_settings(path)
    assert loaded.codec == "av1"
    assert loaded.inbox
