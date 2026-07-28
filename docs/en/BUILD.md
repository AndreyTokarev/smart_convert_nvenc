# Local build (standalone binary)

Русский: [../ru/BUILD.md](../ru/BUILD.md).

## Supported path

Day-to-day use is still **from source**:

```powershell
uv sync
uv run smart-convert-gui
# or
uv run smart-convert path\to\video.mp4
uv run smart-convert-course --profile course
```

Release zips from GitHub Actions are **experimental**. Prefer source until that disclaimer is removed.

## Local Windows exe

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
# optional: also download BtbN FFmpeg n8.1 into the stage folder
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -WithFfmpeg
```

Output: `dist/smart_convert_nvenc-windows-amd64/smart-convert.exe` (+ `ffmpeg/bin/` if `-WithFfmpeg`).

Equivalent one-liner (also used in CI):

```powershell
uv sync --group release
uv run pyinstaller --noconfirm --clean --onefile --name smart-convert `
  --manifest packaging/windows/smart-convert.manifest `
  --collect-all customtkinter --collect-data smart_convert_nvenc `
  scripts/pyi_smart_convert.py
```

## CI release

Tag `v*` (or `workflow_dispatch`) runs [`.github/workflows/release.yml`](../../.github/workflows/release.yml): PyInstaller onefile for Windows / Linux / macOS, stages zip, vendors FFmpeg on Win/Linux via `scripts/fetch_ffmpeg.sh`.

Details: [RELEASES.md](./RELEASES.md).

## Profiles in the binary

Named presets live in the package as `smart_convert_nvenc/data/profiles.toml`. PyInstaller must use `--collect-data smart_convert_nvenc` so `--profile default|course` works in the frozen exe.
