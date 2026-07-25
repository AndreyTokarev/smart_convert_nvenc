#!/usr/bin/env python3
"""Optional NVENC smoke check (not run in CI).

Exit codes:
  0 — hevc_nvenc present (and optional encode succeeded)
  1 — ffmpeg/probe failure or NVENC missing
  2 — encode smoke requested but failed

Usage:
  uv run python scripts/smoke_nvenc.py
  uv run python scripts/smoke_nvenc.py --encode   # short NVENC encode
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from smart_convert_nvenc.encode import encode_file
from smart_convert_nvenc.ffmpeg_tools import ffmpeg_executable
from smart_convert_nvenc.models import (
    AudioSettings,
    EncoderBackend,
    EncodeProfile,
    VideoCodec,
)
from smart_convert_nvenc.probe import (
    ToolError,
    has_hevc_nvenc,
    validate_environment,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NVENC availability smoke check")
    parser.add_argument(
        "--encode",
        action="store_true",
        help="Also encode a tiny synthetic clip with hevc_nvenc",
    )
    args = parser.parse_args(argv)

    try:
        lines = validate_environment(EncoderBackend.GPU)
    except ToolError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    for line in lines:
        print(f"ok: {line}")

    if not has_hevc_nvenc():
        print("FAIL: hevc_nvenc not found", file=sys.stderr)
        return 1
    print("ok: hevc_nvenc present")

    if not args.encode:
        print("smoke: environment only (pass --encode for a short NVENC encode)")
        return 0

    with tempfile.TemporaryDirectory(prefix="smoke_nvenc_") as tmp:
        work = Path(tmp)
        src = work / "src.mp4"
        out = work / "out.mp4"
        gen = subprocess.run(
            [
                ffmpeg_executable(),
                "-hide_banner",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=1",
                "-c:v",
                "libx264",
                "-t",
                "1",
                str(src),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if gen.returncode != 0 or not src.is_file():
            err = (gen.stderr or "")[-400:]
            print(f"FAIL: could not generate test clip: {err}", file=sys.stderr)
            return 2
        try:
            encode_file(
                input_path=src,
                output_path=out,
                profile=EncodeProfile(
                    codec=VideoCodec.HEVC,
                    cq=32,
                    preset="p4",
                    backend=EncoderBackend.GPU,
                ),
                audio=AudioSettings.parse("copy"),
                for_sample=False,
            )
        except Exception as exc:
            print(f"FAIL: NVENC encode: {exc}", file=sys.stderr)
            return 2
        if not out.is_file() or out.stat().st_size < 100:
            print("FAIL: empty NVENC output", file=sys.stderr)
            return 2
        print(f"ok: NVENC encode wrote {out.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
