from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def is_frozen() -> bool:
    """True when running as a PyInstaller (or similar) bundled binary."""
    return bool(getattr(sys, "frozen", False))


def find_project_root(start: Path | None = None) -> Path:
    """Resolve repo root (directory containing pyproject.toml)."""
    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    candidates.append(Path(__file__).resolve())
    candidates.append(Path.cwd().resolve())

    seen: set[Path] = set()
    for base in candidates:
        for path in [base, *base.parents]:
            if path in seen:
                continue
            seen.add(path)
            if (path / "pyproject.toml").is_file():
                return path
    raise RuntimeError("Не найден корень проекта (pyproject.toml).")


def default_data_root() -> Path:
    """Directory used for default ``courses/`` layout.

    - Dev / source install: repo root (``pyproject.toml``).
    - Frozen exe: directory containing the binary (portable zip layout).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return find_project_root()


@dataclass(frozen=True)
class CoursePaths:
    inbox: Path
    outbox: Path
    tmp: Path

    def ensure(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)


def resolve_course_paths(
    *,
    courses_root: Path | None = None,
    inbox: Path | None = None,
    outbox: Path | None = None,
    tmp: Path | None = None,
    project_root: Path | None = None,
) -> CoursePaths:
    env_root = os.environ.get("SMART_CONVERT_COURSES_ROOT")
    env_inbox = os.environ.get("SMART_CONVERT_INBOX")
    env_outbox = os.environ.get("SMART_CONVERT_OUTBOX")
    env_tmp = os.environ.get("SMART_CONVERT_TMP")

    resolved_inbox = inbox or (Path(env_inbox) if env_inbox else None)
    resolved_outbox = outbox or (Path(env_outbox) if env_outbox else None)
    resolved_tmp = tmp or (Path(env_tmp) if env_tmp else None)

    if resolved_inbox is None or resolved_outbox is None or resolved_tmp is None:
        if courses_root is not None:
            base = courses_root
        elif env_root:
            base = Path(env_root)
        else:
            root = project_root or default_data_root()
            base = root / "courses"
        if resolved_inbox is None:
            resolved_inbox = base / "inbox"
        if resolved_outbox is None:
            resolved_outbox = base / "outbox"
        if resolved_tmp is None:
            resolved_tmp = base / "tmp"

    return CoursePaths(
        inbox=resolved_inbox.resolve(),
        outbox=resolved_outbox.resolve(),
        tmp=resolved_tmp.resolve(),
    )
