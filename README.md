# smart_convert_nvenc

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Compress **video course archives** with **NVIDIA NVENC**: race HEVC vs AV1 on a short sample, full-encode only when it saves space, decide at the **course folder** level (`inbox → tmp → outbox`).

Built as a **fast personal MVP**, now open source under **MIT**.

| Language | Docs |
|----------|------|
| **English** | [docs/en/USER_GUIDE.md](docs/en/USER_GUIDE.md) · [docs/en/ARCHITECTURE.md](docs/en/ARCHITECTURE.md) · [docs/en/RELEASES.md](docs/en/RELEASES.md) |
| **Русский** | [docs/ru/USER_GUIDE.md](docs/ru/USER_GUIDE.md) · [docs/ru/ARCHITECTURE.md](docs/ru/ARCHITECTURE.md) · [docs/ru/RELEASES.md](docs/ru/RELEASES.md) |

## Why

Online courses (screen + slides + speech) eat disk. You rarely need cinema-grade encodes — you need **readable slides**, **clear audio**, and **free space** for the next download. This tool batch-compresses whole course trees on an NVIDIA GPU.

## Highlights

- HEVC vs AV1 **sample race** + min-savings gate (honest size@CQ disclaimer, no VMAF in MVP)
- Course pipeline: non-video files preserved; unprofitable courses pass through unchanged
- CLI + CustomTkinter **GUI** (maximized, path pickers, session freed MiB / % / MiB/h)
- Hard **Stop** (Windows process-tree kill), unique temp files, hwaccel retry
- Skip videos already in HEVC/AV1
- Windows sleep / pending-reboot guard while a job runs
- Tests with **≥90%** coverage (GPU not required for CI)

## Requirements

- Windows 10/11 + Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- FFmpeg with `hevc_nvenc` + `av1_nvenc` (RTX 40xx for AV1 encode)
- NVIDIA driver

```powershell
ffmpeg -hide_banner -encoders | findstr nvenc
```

## Quick start

```powershell
git clone https://github.com/AndreyTokarev/smart_convert_nvenc.git
cd smart_convert_nvenc
uv sync

# GUI
uv run smart-convert-gui

# or CLI: all courses in courses/inbox
uv run smart-convert-course

# single file
uv run smart-convert "D:\path\to\lesson.mp4"
```

Default layout:

```text
courses/inbox/   ← drop course folders
courses/tmp/     ← encode scratch
courses/outbox/  ← results
```

## Releases (standalone)

Tag `v*` → GitHub Actions builds Windows / Linux / macOS zips (PyInstaller).  
**FFmpeg + NVIDIA NVENC still required** on the machine. Details: [docs/en/RELEASES.md](docs/en/RELEASES.md).

## License

[MIT](LICENSE) — free to use, modify, and redistribute.

## More documentation

- Index: [docs/README.md](docs/README.md)
- Product decisions: [docs/refactoring-plan.md](docs/refactoring-plan.md)
- Feature port roadmap: [docs/feature-port-plan.md](docs/feature-port-plan.md)
- ADRs: [docs/adr/](docs/adr/)
