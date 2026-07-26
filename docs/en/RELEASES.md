# Releases / standalone builds

English. Русский: [../ru/RELEASES.md](../ru/RELEASES.md).

## Status (early project)

**Standalone binaries are experimental and are not meaningfully tested yet.**  
The project is at the very beginning: the **supported / working** way to run the app is **from source** (`git clone` + `uv sync` + `uv run …`).  
GitHub Release zips are convenience artifacts for later; treat them as **unsupported / use at your own risk** until this note is removed.

### Support bar checklist (R3.3 — before removing “unsupported”)

- [ ] Maintainer runs `uv run python scripts/smoke_nvenc.py --encode` on Windows + NVIDIA (driver OK for bundled FFmpeg n8.1)
- [ ] Smoke a one-file CLI encode and a short course dry-run from the release zip (or from source with the same FFmpeg)
- [ ] Record date / GPU / driver / FFmpeg build in this section
- [ ] Then soften or remove the unsupported wording above

## What GitHub Releases contain

On each git tag `v*` (example: `v0.1.11`), [`.github/workflows/release.yml`](../../.github/workflows/release.yml) builds **PyInstaller** one-file binaries for:

| Artifact zip | Runner | Notes |
|--------------|--------|--------|
| `smart_convert_nvenc-windows-amd64.zip` | `windows-latest` | `.exe` for CLI + GUI |
| `smart_convert_nvenc-linux-amd64.zip` | `ubuntu-latest` | ELF binaries |
| `smart_convert_nvenc-macos-arm64.zip` | `macos-latest` | Apple Silicon (GitHub’s current macOS runners) |

Each zip includes:

- **`smart-convert`** — one binary: GUI (default) / `course …` / `duplicates …` / single file
- `README.md`, `LICENSE`, `README-RELEASE.txt`
- **Windows / Linux:** `ffmpeg/bin/ffmpeg` + `ffprobe` (BtbN GPL **n8.1** static with **`hevc_nvenc` + `av1_nvenc`**, from the floating `latest` tag — not bleeding-edge `master`, which often needs a newer NVENC driver API)
- **macOS:** FFmpeg is **not** bundled (no BtbN macOS artifacts)

## Why four source scripts / why the zip used to have three exes

The app has **four jobs** (source) / one launcher binary (release):

| Job | From source (`uv`) | Release zip (v0.1.4+) |
|-----|--------------------|------------------------|
| One video file | `uv run smart-convert …` | `smart-convert video.mp4 …` |
| Course inbox→outbox | `uv run smart-convert-course …` | `smart-convert course …` |
| Duplicate report | `uv run smart-convert-duplicates …` | `smart-convert duplicates …` |
| Desktop GUI | `uv run smart-convert-gui` | `smart-convert` / `smart-convert gui` |

Those map to four `[project.scripts]` entry points in `pyproject.toml` (`cli`, `course_cli`, `duplicates_cli`, `gui`). That is convenient when developing with `uv`: each command stays small and does not force-load the GUI stack for a simple CLI run.

**Through v0.1.3**, the release zip mirrored CLI/course/GUI 1:1 — PyInstaller built **three** one-file binaries. Same code, three wrappers; the zip looked cluttered and ~tripled download size for little gain for end users.

**From v0.1.4**, the zip ships **one** `smart-convert` binary with a small launcher that dispatches by argv (GUI by default; includes `duplicates` from later tags). The four `uv run …` scripts remain for source installs.

## FFmpeg in the zip

- Win/Linux release zips **include** a recent FFmpeg under `ffmpeg/bin/`. The app prefers that over PATH (`SMART_CONVERT_FFMPEG_DIR` can override).
- FFmpeg binaries are **GPL** (BtbN GPL build); see `ffmpeg/SOURCE.txt` / license files in the zip.
- **NVIDIA drivers are still not shipped.** NVENC needs a suitable GPU + driver on the machine.
- **From source** (`uv run`): install FFmpeg yourself and put it on `PATH` (or set `SMART_CONVERT_FFMPEG_DIR`).

macOS/Linux packages exist so the app can run where Python packaging is awkward, but **NVENC encode is NVIDIA-centric**. On Mac without NVIDIA NVENC, CLI/GUI can start, but encoding will fail environment checks unless a suitable FFmpeg/GPU stack exists.

## How to cut a release

1. Update `__version__` in `src/smart_convert_nvenc/__init__.py` (single source of truth; hatch reads it).
2. Move items from **Unreleased** into a new section in [CHANGELOG.md](../../CHANGELOG.md) and [CHANGELOG.ru.md](../../CHANGELOG.ru.md).
3. Commit, then tag matching the version:

```powershell
git tag v0.1.11
git push origin v0.1.11
```


Or run the **Release** workflow manually (`workflow_dispatch`) from the Actions tab.

CLI/GUI expose the same version via `smart-convert --version` / window title.

## Local build (optional)

```powershell
uv sync --group release
uv run pyinstaller --noconfirm --clean --onefile --name smart-convert `
  --collect-all customtkinter --collect-data smart_convert_nvenc `
  scripts/pyi_smart_convert.py
```

Or: `scripts/build.ps1` (−WithFfmpeg optional). See [BUILD.md](./BUILD.md).

Outputs land in `dist/`. Then optionally: `scripts/fetch_ffmpeg.sh windows-amd64 dist/smart_convert_nvenc-windows-amd64`.
