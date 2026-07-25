from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .course import list_course_dirs, tree_size
from .models import is_video_media


def file_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(roots: Iterable[Path], *, min_size: int = 0) -> Iterator[Path]:
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            if path.stat().st_size < min_size:
                continue
            seen.add(resolved)
            yield path


@dataclass(frozen=True)
class DuplicateFileGroup:
    size_bytes: int
    sha256: str
    paths: tuple[Path, ...]

    @property
    def wasted_bytes(self) -> int:
        if len(self.paths) < 2:
            return 0
        return self.size_bytes * (len(self.paths) - 1)


@dataclass(frozen=True)
class DuplicateNameGroup:
    name: str
    paths: tuple[Path, ...]
    sizes: tuple[int, ...]


@dataclass(frozen=True)
class DuplicateReport:
    roots: tuple[Path, ...]
    file_groups: tuple[DuplicateFileGroup, ...]
    name_groups: tuple[DuplicateNameGroup, ...]

    @property
    def file_group_count(self) -> int:
        return len(self.file_groups)

    @property
    def name_group_count(self) -> int:
        return len(self.name_groups)

    @property
    def wasted_bytes(self) -> int:
        return sum(g.wasted_bytes for g in self.file_groups)


def find_duplicate_files(
    roots: Iterable[Path],
    *,
    min_size: int = 0,
    videos_only: bool = False,
) -> list[DuplicateFileGroup]:
    by_size: dict[int, list[Path]] = defaultdict(list)
    for path in iter_files(roots, min_size=min_size):
        if videos_only and not is_video_media(path):
            continue
        by_size[path.stat().st_size].append(path)

    groups: list[DuplicateFileGroup] = []
    for size, paths in sorted(by_size.items(), key=lambda item: -item[0]):
        if len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in paths:
            by_hash[file_sha256(path)].append(path)
        for digest, hashed in by_hash.items():
            if len(hashed) < 2:
                continue
            ordered = tuple(sorted(hashed, key=lambda p: str(p).lower()))
            groups.append(DuplicateFileGroup(size_bytes=size, sha256=digest, paths=ordered))
    groups.sort(key=lambda g: (-g.wasted_bytes, -g.size_bytes, g.sha256))
    return groups


def find_duplicate_course_names(roots: Iterable[Path]) -> list[DuplicateNameGroup]:
    by_name: dict[str, list[Path]] = defaultdict(list)
    for root in roots:
        if not root.is_dir():
            continue
        for course in list_course_dirs(root, by_size=False):
            by_name[course.name.casefold()].append(course.resolve())

    groups: list[DuplicateNameGroup] = []
    for key, paths in by_name.items():
        unique = sorted(set(paths), key=lambda p: str(p).lower())
        if len(unique) < 2:
            continue
        sizes = tuple(tree_size(p) for p in unique)
        display = unique[0].name
        groups.append(DuplicateNameGroup(name=display, paths=tuple(unique), sizes=sizes))
    groups.sort(key=lambda g: (-sum(g.sizes), g.name.casefold()))
    return groups


def scan_duplicates(
    roots: Iterable[Path],
    *,
    min_size: int = 0,
    videos_only: bool = False,
) -> DuplicateReport:
    root_list = tuple(Path(r).resolve() for r in roots)
    return DuplicateReport(
        roots=root_list,
        file_groups=tuple(
            find_duplicate_files(root_list, min_size=min_size, videos_only=videos_only)
        ),
        name_groups=tuple(find_duplicate_course_names(root_list)),
    )


def format_report(report: DuplicateReport) -> str:
    lines: list[str] = [
        "# Duplicate report",
        "",
        f"Roots: {', '.join(str(r) for r in report.roots)}",
        f"Exact file groups: {report.file_group_count}",
        f"Same course-name groups: {report.name_group_count}",
        f"Potential wasted (exact copies): {report.wasted_bytes / (1024 * 1024):.2f} MiB",
        "",
        "No files were deleted (report only).",
        "",
    ]

    if report.file_groups:
        lines.append("## Exact file duplicates")
        lines.append("")
        for i, group in enumerate(report.file_groups, start=1):
            lines.append(
                f"### Group {i} — {group.size_bytes / (1024 * 1024):.2f} MiB each, "
                f"sha256={group.sha256[:12]}…"
            )
            for path in group.paths:
                lines.append(f"- `{path}`")
            lines.append("")
    else:
        lines.append("## Exact file duplicates")
        lines.append("")
        lines.append("None found.")
        lines.append("")

    if report.name_groups:
        lines.append("## Same course folder name")
        lines.append("")
        for i, group in enumerate(report.name_groups, start=1):
            lines.append(f"### Group {i} — `{group.name}`")
            for path, size in zip(group.paths, group.sizes, strict=True):
                lines.append(f"- `{path}` ({size / (1024 * 1024):.2f} MiB)")
            lines.append("")
    else:
        lines.append("## Same course folder name")
        lines.append("")
        lines.append("None found.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
