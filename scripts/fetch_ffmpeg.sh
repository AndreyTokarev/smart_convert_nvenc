#!/usr/bin/env bash
# Download BtbN FFmpeg "latest" GPL static build and stage ffmpeg/bin (+ license).
# Usage:
#   scripts/fetch_ffmpeg.sh <windows-amd64|linux-amd64> <output_dir>
# Example:
#   scripts/fetch_ffmpeg.sh windows-amd64 dist/smart_convert_nvenc-windows-amd64
set -euo pipefail

TARGET="${1:-}"
OUT="${2:-}"

if [[ -z "$TARGET" || -z "$OUT" ]]; then
  echo "Usage: $0 <windows-amd64|linux-amd64> <output_dir>" >&2
  exit 2
fi

BASE_URL="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

# Prefer release branch over master: master often requires a newer NVENC API
# than drivers currently installed (e.g. API 13.1 vs 13.0).
case "$TARGET" in
  windows-amd64)
    ARCHIVE="ffmpeg-n7.1-latest-win64-gpl-7.1.zip"
    EXTRACT_CMD=(unzip -q)
    ;;
  linux-amd64)
    ARCHIVE="ffmpeg-n7.1-latest-linux64-gpl-7.1.tar.xz"
    EXTRACT_CMD=(tar -xJf)
    ;;
  macos-arm64)
    echo "No BtbN macOS build; skip bundling FFmpeg for $TARGET" >&2
    exit 0
    ;;
  *)
    echo "Unknown target: $TARGET" >&2
    exit 2
    ;;
esac

echo "Downloading $ARCHIVE ..."
curl -fsSL -o "$WORKDIR/$ARCHIVE" "$BASE_URL/$ARCHIVE"
mkdir -p "$WORKDIR/extract"
(
  cd "$WORKDIR/extract"
  "${EXTRACT_CMD[@]}" "$WORKDIR/$ARCHIVE"
)

# BtbN layout: <prefix>/bin/ffmpeg
FOUND_BIN="$(find "$WORKDIR/extract" -type d -name bin | head -n 1)"
if [[ -z "$FOUND_BIN" ]]; then
  echo "Could not find bin/ inside $ARCHIVE" >&2
  exit 1
fi
PREFIX="$(dirname "$FOUND_BIN")"

DEST="$OUT/ffmpeg"
mkdir -p "$DEST/bin"
# Copy tools (skip ffplay)
for tool in ffmpeg ffprobe; do
  if [[ -f "$FOUND_BIN/$tool.exe" ]]; then
    cp "$FOUND_BIN/$tool.exe" "$DEST/bin/"
  elif [[ -f "$FOUND_BIN/$tool" ]]; then
    cp "$FOUND_BIN/$tool" "$DEST/bin/"
    chmod +x "$DEST/bin/$tool"
  else
    echo "Missing $tool in $FOUND_BIN" >&2
    exit 1
  fi
done

# License / README from the FFmpeg package (best-effort)
for name in LICENSE LICENSE.txt COPYING COPYING.GPLv3 README.txt README.md; do
  if [[ -f "$PREFIX/$name" ]]; then
    cp "$PREFIX/$name" "$DEST/"
  fi
done

# Always leave a short provenance note
{
  echo "FFmpeg binaries from BtbN/FFmpeg-Builds (GPL static)."
  echo "Source archive: $ARCHIVE"
  echo "URL: $BASE_URL/$ARCHIVE"
  echo "Downloaded at build time from the floating 'latest' tag (release branch n7.1, not master)."
} > "$DEST/SOURCE.txt"

echo "Staged FFmpeg into $DEST/bin"
ls -la "$DEST/bin"
