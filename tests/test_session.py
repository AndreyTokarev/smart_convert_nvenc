from __future__ import annotations

import time
from pathlib import Path

from smart_convert_nvenc.session import (
    SessionStats,
    default_session_report_path,
    format_gib_or_mib,
    format_mib,
    savings_ratio,
    write_session_report,
)


def test_formatters() -> None:
    assert "MiB" in format_mib(5 * 1024 * 1024)
    assert "GiB" in format_gib_or_mib(2 * 1024 * 1024 * 1024)
    assert savings_ratio(1000, 600) == 0.4
    assert savings_ratio(0, 0) == 0.0


def test_session_stats_accumulates() -> None:
    stats = SessionStats(started_at=time.perf_counter() - 3600)
    stats.add_course("A", 1000, 400)
    stats.add_course("B", 2000, 1500)
    assert stats.freed_bytes == 1100
    assert stats.ratio == savings_ratio(3000, 1900)
    assert stats.last_course() is not None
    assert stats.last_course().name == "B"
    assert stats.mib_per_hour > 0
    line = stats.summary_line()
    assert "Session:" in line
    assert "freed" in line


def test_markdown_session_report(tmp_path: Path) -> None:
    stats = SessionStats(started_at=time.perf_counter() - 60)
    stats.add_course(
        "Course|One",
        10 * 1024 * 1024,
        4 * 1024 * 1024,
        compressed=True,
        videos_compressed=2,
        videos_total=3,
        outbox_path=str(tmp_path / "out" / "Course"),
    )
    text = stats.markdown_report()
    assert "# Session report" in text
    assert "Course\\|One" in text
    assert "| Title |" in text
    assert "2/3" in text
    path = write_session_report(stats, tmp_path / "session-report.md")
    assert path.read_text(encoding="utf-8") == text
    assert default_session_report_path(inbox=tmp_path / "inbox") == tmp_path / "session-report.md"


def test_markdown_empty_session() -> None:
    text = SessionStats().markdown_report()
    assert "No courses processed." in text
