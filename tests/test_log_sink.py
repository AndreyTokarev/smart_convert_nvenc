from __future__ import annotations

from pathlib import Path

from smart_convert_nvenc.log_sink import FileLogSink, default_app_log_path, tee_log


def test_tee_log_without_path_is_identity() -> None:
    lines: list[str] = []
    log = tee_log(lines.append, None)
    log("hello")
    assert lines == ["hello"]


def test_tee_log_appends_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "run.log"
    lines: list[str] = []
    log = tee_log(lines.append, path)
    log("one")
    log("two\n")
    assert lines == ["one", "two\n"]
    text = path.read_text(encoding="utf-8")
    assert text.splitlines() == ["one", "two"]


def test_file_log_sink_context(tmp_path: Path) -> None:
    path = tmp_path / "a.log"
    with FileLogSink(path) as sink:
        sink("line")
    assert path.read_text(encoding="utf-8") == "line\n"


def test_default_app_log_path_next_to_settings(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SMART_CONVERT_APPDATA", str(tmp_path))
    assert default_app_log_path() == (tmp_path / "smart_convert_nvenc" / "app.log").resolve()
