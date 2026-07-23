"""Backward-compatible entry; prefer `uv run smart-convert`. """

from smart_convert_nvenc.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
