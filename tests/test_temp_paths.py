from __future__ import annotations

from pathlib import Path

import pytest

from smart_convert_nvenc.temp_paths import (
    cleanup_conversion_temps,
    is_conversion_temp_path,
    make_conversion_temp,
    parse_conversion_temp,
    promote_temp_to_final,
)


def test_make_and_parse_conversion_temp(tmp_path: Path) -> None:
    final = tmp_path / "out.mp4"
    temp = make_conversion_temp(final)
    assert is_conversion_temp_path(temp)
    parsed = parse_conversion_temp(temp)
    assert parsed is not None
    stem, _rid, suffix = parsed
    assert stem == "out"
    assert suffix == ".mp4"
    assert not is_conversion_temp_path(final)
    assert parse_conversion_temp(final) is None


def test_promote_temp_to_final(tmp_path: Path) -> None:
    final = tmp_path / "nested" / "out.mp4"
    temp = make_conversion_temp(tmp_path / "out.mp4")
    temp.write_bytes(b"encoded")
    promote_temp_to_final(temp, final)
    assert final.read_bytes() == b"encoded"
    assert not temp.exists()


def test_promote_replaces_existing(tmp_path: Path) -> None:
    final = tmp_path / "out.mp4"
    final.write_bytes(b"old")
    temp = make_conversion_temp(final)
    temp.write_bytes(b"new")
    promote_temp_to_final(temp, final)
    assert final.read_bytes() == b"new"


def test_promote_rejects_empty(tmp_path: Path) -> None:
    final = tmp_path / "out.mp4"
    temp = make_conversion_temp(final)
    temp.write_bytes(b"")
    with pytest.raises(OSError, match="Empty encode"):
        promote_temp_to_final(temp, final)
    assert not temp.exists()


def test_promote_missing_temp(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        promote_temp_to_final(tmp_path / "missing.conv.1.mp4", tmp_path / "out.mp4")


def test_cleanup_conversion_temps(tmp_path: Path) -> None:
    keep = tmp_path / "keep.mp4"
    keep.write_bytes(b"k")
    orphan = make_conversion_temp(tmp_path / "x.mkv")
    orphan.write_bytes(b"z")
    nested = tmp_path / "sub"
    nested.mkdir()
    nested_orphan = make_conversion_temp(nested / "y.mp4")
    nested_orphan.write_bytes(b"y")
    removed = cleanup_conversion_temps(tmp_path)
    assert orphan in removed
    assert nested_orphan in removed
    assert keep.exists()
    assert cleanup_conversion_temps(tmp_path / "missing") == []
