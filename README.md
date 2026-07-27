# smart_convert_nvenc

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.12-blue.svg)](CHANGELOG.md)

**[English](README.md)** · **[Русский](README.ru.md)**

Compress **video course archives** with **NVIDIA NVENC**: race HEVC vs AV1 on a short sample, full-encode only when it saves space, decide at the **course folder** level (`inbox → tmp → outbox`).

Built as a **fast personal MVP**, now open source under **MIT**.

Current version: **0.1.12** — see [CHANGELOG.md](CHANGELOG.md) · [CHANGELOG.ru.md](CHANGELOG.ru.md).

| Language | Docs |
|----------|------|
| **English** | [USER_GUIDE](docs/en/USER_GUIDE.md) · [ARCHITECTURE](docs/en/ARCHITECTURE.md) · [RELEASES](docs/en/RELEASES.md) · [BUILD](docs/en/BUILD.md) · [ADRs](docs/en/adr/README.md) |
| **Русский** | [руководство](docs/ru/USER_GUIDE.md) · [архитектура](docs/ru/ARCHITECTURE.md) · [релизы](docs/ru/RELEASES.md) · [сборка](docs/ru/BUILD.md) · [ADR](docs/ru/adr/README.md) |

Full index: [docs/README.md](docs/README.md).

## Why

Online courses (screen + slides + speech) eat disk. You rarely need cinema-grade encodes — you need **readable slides**, **clear audio**, and **free space** for the next download. This tool batch-compresses whole course trees on an NVIDIA GPU (or CPU encoders when chosen).

## Highlights

- HEVC vs AV1 **sample race** + min-savings gate; optional **hybrid VMAF** when FFmpeg has `libvmaf` (`--vmaf auto|off|on`)
- Course pipeline: non-video preserved; unprofitable courses pass through unchanged
- Named **profiles** (`default` / `course`) via `--profile`
- Encoder modes: **gpu** / **cpu** / **auto**
- Duplicate **report** (no delete): `smart-convert duplicates`
- Overwrite existing outbox courses by default
- Session Markdown report after a course batch (`session-report.md`)
- CLI + CustomTkinter **GUI** (paths, queue, logs, session freed MiB / % / MiB/h)
- Hard **Stop**, unique temps, hwaccel retry, Windows sleep/reboot guard
- Tests with **≥90%** coverage (GPU not required for CI)

## Requirements

- Windows 10/11 + Python 3.12+ (primary; Linux/macOS packaging exists)
- [uv](https://github.com/astral-sh/uv)
- FFmpeg:
  - **GPU (default):** `hevc_nvenc` required; `av1_nvenc` optional (else AV1 via **libsvtav1**)
  - **CPU / auto:** `libx265` + `libsvtav1`
- NVIDIA driver when using GPU (RTX 40-series for hardware AV1 encode)

```powershell
ffmpeg -hide_banner -encoders | findstr /i "nvenc libx265 libsvtav1"
```

## Quick start

```powershell
git clone https://github.com/AndreyTokarev/smart_convert_nvenc.git
cd smart_convert_nvenc
uv sync

uv run smart-convert-gui
uv run smart-convert-course --profile course
uv run smart-convert "D:\path\to\lesson.mp4" --vmaf auto
uv run smart-convert-duplicates
```

Default layout:

```text
courses/inbox/   ← drop course folders
courses/tmp/     ← encode scratch
courses/outbox/  ← results
```

## Releases (standalone)

Tag `v*` → GitHub Actions builds Windows / Linux / macOS zips (PyInstaller).  
**Early project:** binary releases are **experimental**; prefer **from source**.  
**One binary** `smart-convert` (GUI / `course` / `duplicates` / file). Win/Linux ship FFmpeg **n8.1** under `ffmpeg/bin/`. Details: [docs/en/RELEASES.md](docs/en/RELEASES.md) · [docs/en/BUILD.md](docs/en/BUILD.md).

## License

[MIT](LICENSE) — free to use, modify, and redistribute.

## Author

Andrey Tokarev — [GitHub](https://github.com/AndreyTokarev)
