"""Optional file append sink for app logs (CLI/GUI can share)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .gui_settings import default_settings_path


class FileLogSink:
    """Append-only UTF-8 log file. Safe to call from one writer thread."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8", newline="\n")

    def write(self, message: str) -> None:
        self._fh.write(message.rstrip("\n") + "\n")
        self._fh.flush()

    def __call__(self, message: str) -> None:
        self.write(message)

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> FileLogSink:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def tee_log(
    primary: Callable[[str], None],
    path: Path | None,
) -> Callable[[str], None]:
    """Return a log callable that writes to primary and optional file."""
    if path is None:
        return primary
    sink = FileLogSink(path)

    def _log(message: str) -> None:
        primary(message)
        sink.write(message)

    return _log


def default_app_log_path() -> Path:
    """Suggested path under the same config root as GUI settings."""
    return default_settings_path().with_name("app.log")
