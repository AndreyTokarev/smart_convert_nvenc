from __future__ import annotations

import json
from pathlib import Path

from smart_convert_nvenc import duplicates_cli
from smart_convert_nvenc.duplicates import (
    DuplicateFileGroup,
    find_duplicate_course_names,
    find_duplicate_files,
    format_report,
    iter_files,
    scan_duplicates,
)


def test_find_duplicate_files_by_hash(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    payload = b"same-bytes" * 2000
    (a / "one.bin").write_bytes(payload)
    (b / "two.bin").write_bytes(payload)
    (a / "unique.bin").write_bytes(b"other" * 2000)

    groups = find_duplicate_files([a, b], min_size=0)
    assert len(groups) == 1
    assert groups[0].size_bytes == len(payload)
    assert len(groups[0].paths) == 2
    assert groups[0].wasted_bytes == len(payload)


def test_same_size_different_content_not_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.bin").write_bytes(b"aaaa")
    (root / "b.bin").write_bytes(b"bbbb")
    assert find_duplicate_files([root], min_size=0) == []


def test_videos_only_skips_non_video(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    data = b"x" * 100
    (root / "a.bin").write_bytes(data)
    (root / "b.bin").write_bytes(data)
    (root / "a.mp4").write_bytes(data)
    (root / "b.mp4").write_bytes(data)

    all_groups = find_duplicate_files([root], min_size=0, videos_only=False)
    video_groups = find_duplicate_files([root], min_size=0, videos_only=True)
    assert sum(len(g.paths) for g in all_groups) == 4
    assert sum(len(g.paths) for g in video_groups) == 2


def test_find_duplicate_course_names(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    (inbox / "Course A").mkdir(parents=True)
    (outbox / "course a").mkdir(parents=True)
    (inbox / "Unique").mkdir(parents=True)
    (inbox / "Course A" / "note.txt").write_text("x", encoding="utf-8")
    (outbox / "course a" / "note.txt").write_text("yyyy", encoding="utf-8")

    groups = find_duplicate_course_names([inbox, outbox, tmp_path / "missing"])
    assert len(groups) == 1
    assert groups[0].name.casefold() == "course a"
    assert len(groups[0].paths) == 2

    report = scan_duplicates([inbox, outbox], min_size=0)
    text = format_report(report)
    assert "Same course folder name" in text
    assert "Course A" in text or "course a" in text


def test_find_duplicate_course_titles(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    a = inbox / "Folder A"
    b = outbox / "Folder B"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    payload = {
        "schema": 1,
        "title": "Same Title",
        "publishers": ["Acme"],
        "authors": [],
        "notes": "",
    }
    (a / "course.json").write_text(json.dumps(payload), encoding="utf-8")
    (b / "course.json").write_text(json.dumps(payload), encoding="utf-8")
    (a / "note.txt").write_text("x", encoding="utf-8")
    (b / "note.txt").write_text("y", encoding="utf-8")

    from smart_convert_nvenc.duplicates import find_duplicate_course_titles

    groups = find_duplicate_course_titles([inbox, outbox])
    assert len(groups) == 1
    assert groups[0].title == "Same Title"
    assert groups[0].publishers_overlap is True
    report = scan_duplicates([inbox, outbox], min_size=0)
    text = format_report(report)
    assert "Same course.json title" in text
    assert "Same Title" in text


def test_format_report_empty(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    report = scan_duplicates([root], min_size=0)
    text = format_report(report)
    assert "Exact file groups: 0" in text
    assert "None found." in text
    assert "No files were deleted" in text


def test_iter_files_skips_and_dedupes(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "sub").mkdir()
    (root / "tiny.bin").write_bytes(b"x")
    big = root / "big.bin"
    big.write_bytes(b"y" * 100)
    files = list(iter_files([tmp_path / "missing", root, root], min_size=50))
    assert len(files) == 1
    assert files[0].name == "big.bin"


def test_singleton_group_wasted_zero() -> None:
    group = DuplicateFileGroup(size_bytes=10, sha256="abc", paths=(Path("only"),))
    assert group.wasted_bytes == 0


def test_duplicates_cli_writes_output(tmp_path: Path) -> None:
    root = tmp_path / "scan"
    root.mkdir()
    payload = b"dup" * 5000
    (root / "1.bin").write_bytes(payload)
    (root / "2.bin").write_bytes(payload)
    out = tmp_path / "report.md"
    code = duplicates_cli.main([str(root), "--min-size", "0", "-o", str(out)])
    assert code == 0
    assert out.is_file()
    assert "Exact file groups: 1" in out.read_text(encoding="utf-8")


def test_duplicates_cli_default_inbox_outbox(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()
    code = duplicates_cli.main(
        ["--inbox", str(inbox), "--outbox", str(outbox), "--min-size", "0"]
    )
    assert code == 0


def test_duplicates_cli_no_existing_roots(tmp_path: Path) -> None:
    code = duplicates_cli.main(
        [
            "--inbox",
            str(tmp_path / "no-inbox"),
            "--outbox",
            str(tmp_path / "no-outbox"),
        ]
    )
    assert code == 1


def test_duplicates_cli_missing_root(tmp_path: Path) -> None:
    assert duplicates_cli.main([str(tmp_path / "missing")]) == 1
