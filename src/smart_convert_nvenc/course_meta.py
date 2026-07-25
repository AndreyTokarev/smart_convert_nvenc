"""Load optional course.json metadata (ADR-0002). Single parser for GUI/reports/duplicates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COURSE_JSON_NAME = "course.json"


@dataclass(frozen=True)
class CourseMeta:
    schema: int
    title: str
    year: int | None
    publishers: tuple[str, ...]
    authors: tuple[str, ...]
    notes: str


def normalize_title(value: str) -> str:
    """Collapse whitespace and case for duplicate matching."""
    collapsed = re.sub(r"\s+", " ", value.strip())
    return collapsed.casefold()


def publishers_overlap(a: CourseMeta, b: CourseMeta) -> bool:
    if not a.publishers or not b.publishers:
        return False
    left = {normalize_title(p) for p in a.publishers if p.strip()}
    right = {normalize_title(p) for p in b.publishers if p.strip()}
    return bool(left & right)


def display_label(folder_name: str, meta: CourseMeta | None) -> str:
    """Human label for lists; folder name remains filesystem identity."""
    if meta is None or not meta.title.strip():
        return folder_name
    title = meta.title.strip()
    if title.casefold() == folder_name.casefold():
        return folder_name
    return f"{folder_name} — {title}"


def tooltip_text(folder_name: str, meta: CourseMeta | None, *, size_mib: float) -> str:
    lines = [folder_name, f"{size_mib:.0f} MiB"]
    if meta is None:
        return "\n".join(lines)
    if meta.title.strip():
        lines.append(f"Title: {meta.title.strip()}")
    if meta.year is not None:
        lines.append(f"Year: {meta.year}")
    if meta.publishers:
        lines.append("Publishers: " + ", ".join(meta.publishers))
    if meta.authors:
        lines.append("Authors: " + ", ".join(meta.authors))
    if meta.notes.strip():
        lines.append(meta.notes.strip())
    return "\n".join(lines)


def _as_str_list(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        text = raw.strip()
        return (text,) if text else ()
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return tuple(out)
    return ()


def _parse_year(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            return int(raw.strip())
        except ValueError:
            return None
    return None


def course_meta_from_mapping(data: dict[str, Any]) -> CourseMeta | None:
    if not isinstance(data, dict):
        return None
    title = data.get("title")
    if not isinstance(title, str):
        title = ""
    schema_raw = data.get("schema", 1)
    try:
        schema = int(schema_raw)
    except (TypeError, ValueError):
        schema = 1
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        notes = ""
    return CourseMeta(
        schema=schema,
        title=title,
        year=_parse_year(data.get("year")),
        publishers=_as_str_list(data.get("publishers")),
        authors=_as_str_list(data.get("authors")),
        notes=notes,
    )


def load_course_meta(course_root: Path) -> CourseMeta | None:
    """Return metadata if ``course.json`` exists and parses; else None."""
    path = course_root / COURSE_JSON_NAME
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return course_meta_from_mapping(raw)
