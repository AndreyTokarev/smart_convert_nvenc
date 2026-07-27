from __future__ import annotations

import json
from pathlib import Path

from smart_convert_nvenc.course_meta import (
    CourseMeta,
    course_meta_from_mapping,
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
    assert "Year: 2020" in tip
    assert tip.endswith("guitar")


def test_display_label_and_tooltip_fallbacks() -> None:
    assert display_label("Folder", None) == "Folder"
    empty = CourseMeta(1, "  ", None, (), (), "")
    assert display_label("Folder", empty) == "Folder"
    same = CourseMeta(1, "Folder", 2015, (), (), "")
    assert display_label("Folder", same) == "Folder"
    assert tooltip_text("Only", None, size_mib=3.2) == "Only\n3 MiB"


def test_normalize_and_publishers_overlap() -> None:
    a = CourseMeta(1, "Foo", None, ("Acme Pub",), (), "")
    b = CourseMeta(1, "Bar", None, ("acme  pub",), (), "")
    c = CourseMeta(1, "Baz", None, ("Other",), (), "")
    empty = CourseMeta(1, "X", None, (), (), "")
    assert normalize_title("  Foo   Bar ") == "foo bar"
    assert publishers_overlap(a, b) is True
    assert publishers_overlap(a, c) is False
    assert publishers_overlap(a, empty) is False


def test_course_meta_from_mapping_coerces_fields() -> None:
    meta = course_meta_from_mapping(
        {
            "schema": "2",
            "title": 123,
            "year": "2019",
            "publishers": "Solo Pub",
            "authors": ["", "  Alice  ", 7],
            "notes": None,
        }
    )
    assert meta is not None
    assert meta.schema == 2
    assert meta.title == ""
    assert meta.year == 2019
    assert meta.publishers == ("Solo Pub",)
    assert meta.authors == ("Alice",)
    assert meta.notes == ""
    assert course_meta_from_mapping({"year": True}).year is None  # type: ignore[union-attr]
    assert course_meta_from_mapping({"year": 2018.0}).year == 2018  # type: ignore[union-attr]
    assert course_meta_from_mapping({"year": "nope"}).year is None  # type: ignore[union-attr]
    assert course_meta_from_mapping({"schema": object()}).schema == 1  # type: ignore[union-attr]


def test_invalid_json_returns_none(tmp_path: Path) -> None:
    root = tmp_path / "Bad"
    root.mkdir()
    (root / "course.json").write_text("{not-json", encoding="utf-8")
    assert load_course_meta(root) is None


def test_non_object_json_returns_none(tmp_path: Path) -> None:
    root = tmp_path / "List"
    root.mkdir()
    (root / "course.json").write_text("[1, 2]", encoding="utf-8")
    assert load_course_meta(root) is None
