from __future__ import annotations

import json
from pathlib import Path

from smart_convert_nvenc.course_meta import (
    CourseMeta,
    display_label,
    load_course_meta,
    normalize_title,
    publishers_overlap,
    tooltip_text,
)


def test_load_course_meta_missing(tmp_path: Path) -> None:
    assert load_course_meta(tmp_path / "Course") is None


def test_load_course_meta_roundtrip(tmp_path: Path) -> None:
    root = tmp_path / "Sick Licks"
    root.mkdir()
    (root / "course.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "title": "20 Sick Licks",
                "year": 2020,
                "publishers": ["Jam Track Central"],
                "authors": ["Matteo Mancuso"],
                "notes": "guitar",
            }
        ),
        encoding="utf-8",
    )
    meta = load_course_meta(root)
    assert meta is not None
    assert meta.title == "20 Sick Licks"
    assert meta.year == 2020
    assert meta.publishers == ("Jam Track Central",)
    assert meta.authors == ("Matteo Mancuso",)
    assert display_label(root.name, meta) == "Sick Licks — 20 Sick Licks"
    tip = tooltip_text(root.name, meta, size_mib=12)
    assert "Jam Track Central" in tip
    assert "20 Sick Licks" in tip


def test_normalize_and_publishers_overlap() -> None:
    a = CourseMeta(1, "Foo", None, ("Acme Pub",), (), "")
    b = CourseMeta(1, "Bar", None, ("acme  pub",), (), "")
    c = CourseMeta(1, "Baz", None, ("Other",), (), "")
    assert normalize_title("  Foo   Bar ") == "foo bar"
    assert publishers_overlap(a, b) is True
    assert publishers_overlap(a, c) is False


def test_invalid_json_returns_none(tmp_path: Path) -> None:
    root = tmp_path / "Bad"
    root.mkdir()
    (root / "course.json").write_text("{not-json", encoding="utf-8")
    assert load_course_meta(root) is None
