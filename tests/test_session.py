from __future__ import annotations

import time

from smart_convert_nvenc.session import (
    SessionStats,
    format_gib_or_mib,
    format_mib,
    savings_ratio,
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
