from __future__ import annotations

import re
import time
from pathlib import Path

_CONV_TEMP_RE = re.compile(r"^(.+)\.conv\.(\d+)(\.[^.]+)$", re.IGNORECASE)


def make_conversion_temp(final_path: Path) -> Path:
    """Unique temp beside the intended final output: name.conv.<id>.ext"""
    rid = time.time_ns() % 1_000_000_000
    return final_path.with_name(f"{final_path.stem}.conv.{rid}{final_path.suffix}")


def parse_conversion_temp(path: Path) -> tuple[str, int, str] | None:
    match = _CONV_TEMP_RE.match(path.name)
    if not match:
        return None
    return match.group(1), int(match.group(2)), match.group(3)


def is_conversion_temp_path(path: Path) -> bool:
    return parse_conversion_temp(path) is not None


def _safe_unlink(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def cleanup_conversion_temps(root: Path) -> list[Path]:
    """Remove leftover *.conv.* files under root (e.g. courses/tmp)."""
    if not root.exists():
        return []
    removed: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and is_conversion_temp_path(path):
            if _safe_unlink(path):
                removed.append(path)
    return removed


def promote_temp_to_final(temp_path: Path, final_path: Path) -> Path:
    if not temp_path.is_file():
        raise FileNotFoundError(temp_path)
    if temp_path.stat().st_size == 0:
        _safe_unlink(temp_path)
        raise OSError(f"Empty encode output: {temp_path}")
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if final_path.exists():
        final_path.unlink()
    temp_path.replace(final_path)
    return final_path
