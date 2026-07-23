from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    root = project_root or find_project_root()

    env_root = os.environ.get("SMART_CONVERT_COURSES_ROOT")
    env_inbox = os.environ.get("SMART_CONVERT_INBOX")
    env_outbox = os.environ.get("SMART_CONVERT_OUTBOX")
    env_tmp = os.environ.get("SMART_CONVERT_TMP")

    base = courses_root or (Path(env_root) if env_root else root / "courses")

    return CoursePaths(
        inbox=(inbox or (Path(env_inbox) if env_inbox else base / "inbox")).resolve(),
        outbox=(outbox or (Path(env_outbox) if env_outbox else base / "outbox")).resolve(),
        tmp=(tmp or (Path(env_tmp) if env_tmp else base / "tmp")).resolve(),
    )
