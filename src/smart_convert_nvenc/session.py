from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def format_mib(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.1f} MiB"


def format_gib_or_mib(size_bytes: int) -> str:
    if abs(size_bytes) >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GiB"
    return format_mib(size_bytes)


def savings_ratio(original: int, final: int) -> float:
    if original <= 0:
        return 0.0
    return 1.0 - (final / original)


@dataclass
class CourseSavings:
    name: str
    original_bytes: int
    final_bytes: int
    compressed: bool = True
    videos_compressed: int = 0
    videos_total: int = 0
    outbox_path: str | None = None

    @property
    def freed_bytes(self) -> int:
        return max(0, self.original_bytes - self.final_bytes)

    @property
    def ratio(self) -> float:
        return savings_ratio(self.original_bytes, self.final_bytes)


@dataclass
class SessionStats:
    """Accumulate freed space across courses in one GUI/CLI run."""

    started_at: float = field(default_factory=time.perf_counter)
    courses: list[CourseSavings] = field(default_factory=list)

    def add_course(
        self,
        name: str,
        original_bytes: int,
        final_bytes: int,
        *,
        compressed: bool = True,
        videos_compressed: int = 0,
        videos_total: int = 0,
        outbox_path: str | None = None,
    ) -> CourseSavings:
        item = CourseSavings(
            name=name,
            original_bytes=original_bytes,
            final_bytes=final_bytes,
            compressed=compressed,
            videos_compressed=videos_compressed,
            videos_total=videos_total,
            outbox_path=outbox_path,
        )
        self.courses.append(item)
        return item

    @property
    def original_bytes(self) -> int:
        return sum(c.original_bytes for c in self.courses)

    @property
    def final_bytes(self) -> int:
        return sum(c.final_bytes for c in self.courses)

    @property
    def freed_bytes(self) -> int:
        return max(0, self.original_bytes - self.final_bytes)

    @property
    def ratio(self) -> float:
        return savings_ratio(self.original_bytes, self.final_bytes)

    @property
    def elapsed_sec(self) -> float:
        return max(0.001, time.perf_counter() - self.started_at)

    @property
    def mib_per_hour(self) -> float:
        hours = self.elapsed_sec / 3600.0
        return (self.freed_bytes / (1024 * 1024)) / hours if hours > 0 else 0.0

    def last_course(self) -> CourseSavings | None:
        return self.courses[-1] if self.courses else None

    def summary_line(self) -> str:
        return (
            f"Session: freed {format_gib_or_mib(self.freed_bytes)} "
            f"({self.ratio * 100:.1f}%) in {self.elapsed_sec / 60:.1f} min "
            f"({self.mib_per_hour:.0f} MiB/h), courses={len(self.courses)}"
        )

    def markdown_report(self) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            "# Session report",
            "",
            f"Generated: {stamp}",
            "",
            "## Summary",
            "",
            f"- Courses: {len(self.courses)}",
            f"- Original: {format_gib_or_mib(self.original_bytes)}",
            f"- Final: {format_gib_or_mib(self.final_bytes)}",
            f"- Freed: {format_gib_or_mib(self.freed_bytes)} ({self.ratio * 100:.1f}%)",
            f"- Duration: {self.elapsed_sec / 60:.1f} min",
            f"- Throughput: {self.mib_per_hour:.0f} MiB/h",
            "",
            "## Courses",
            "",
        ]
        if not self.courses:
            lines.append("No courses processed.")
            lines.append("")
        else:
            lines.append("| Course | Before | After | Freed | Videos | Compressed | Outbox |")
            lines.append("|--------|--------|-------|-------|--------|------------|--------|")
            for course in self.courses:
                vids = (
                    f"{course.videos_compressed}/{course.videos_total}"
                    if course.videos_total
                    else "—"
                )
                out = f"`{course.outbox_path}`" if course.outbox_path else "—"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            course.name.replace("|", "\\|"),
                            format_gib_or_mib(course.original_bytes),
                            format_gib_or_mib(course.final_bytes),
                            format_gib_or_mib(course.freed_bytes),
                            vids,
                            "yes" if course.compressed else "no",
                            out,
                        ]
                    )
                    + " |"
                )
            lines.append("")
        return "\n".join(lines)


def default_session_report_path(*, inbox: Path) -> Path:
    """Write next to inbox/outbox (``courses/session-report.md``)."""
    return inbox.parent / "session-report.md"


def write_session_report(stats: SessionStats, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stats.markdown_report(), encoding="utf-8")
    return path
