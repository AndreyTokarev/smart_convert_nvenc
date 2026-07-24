from __future__ import annotations

import time
from dataclasses import dataclass, field


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

    def add_course(self, name: str, original_bytes: int, final_bytes: int) -> CourseSavings:
        item = CourseSavings(name=name, original_bytes=original_bytes, final_bytes=final_bytes)
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
