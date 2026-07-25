# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Русский: [CHANGELOG.ru.md](./CHANGELOG.ru.md).

## [Unreleased]

### Added

- Named encode presets in `profiles.toml` (`default`, `course`) with CLI `--profile` (flags override).
- Local Windows build helper `scripts/build.ps1` and `docs/*/BUILD.md`.
- Duplicate scanner (report only): `smart-convert duplicates` / `smart-convert-duplicates` — exact file copies (size+SHA-256) and same course folder names across inbox/outbox.
- Course batch writes `session-report.md` (Markdown totals + per-course table); `--session-report PATH` / `--no-session-report`.

### Changed

### Fixed

### Removed

## [0.1.6] — 2026-07-25

### Changed

- Bundle BtbN **n8.1** FFmpeg (includes **`hevc_nvenc` + `av1_nvenc`**). Verified on current NVIDIA drivers; still keeps libsvtav1 as fallback if `av1_nvenc` is missing.

## [0.1.5] — 2026-07-25

### Fixed

- GPU mode no longer requires `av1_nvenc`. Bundled FFmpeg n7.1 had HEVC NVENC only; when `av1_nvenc` is missing, AV1 race/encode uses **libsvtav1** (CPU) so AV1 stays available.
- Startup no longer falsely reports “NVENC unavailable” on builds that only ship `hevc_nvenc`.

## [0.1.4] — 2026-07-25

### Added

- Single release binary `smart-convert`: GUI (default), `course …`, or one video file.

### Changed

- Bundle BtbN **n7.1** FFmpeg (not `master`) so NVENC works on slightly older drivers.
- NVENC AQ flags use `-spatial-aq` / `-temporal-aq` (required by recent FFmpeg builds).

### Fixed

- FFmpeg errors now include the last lines of ffmpeg output (so NVENC/driver messages are visible).

## [0.1.3] — 2026-07-25

### Added

- Encoder mode `gpu` (default) / `cpu` / `auto`: force libx265 + libsvtav1, or auto-fallback when NVENC is missing (`--encoder`, GUI Encoder menu).
- Release zips for Windows/Linux bundle BtbN GPL FFmpeg under `ffmpeg/bin/` (latest at build time); app prefers bundled binaries over PATH (`SMART_CONVERT_FFMPEG_DIR` override).

### Changed

- Docs state that standalone binaries are early/experimental; the supported run path remains from source.

### Fixed

- Frozen GUI/CLI binaries no longer require `pyproject.toml`; default `courses/` is created next to the executable.

## [0.1.2] — 2026-07-25

### Added

- Queue ordering by size: videos inside a course and courses in CLI/GUI run largest-first so freed space shows up sooner.
- FFmpeg `speed=` shown in the GUI file progress line (e.g. `encode 45% 12.9x`).
- GUI log ring-buffers (app 2000 / FFmpeg 1000 lines) so overnight runs do not grow Textboxes without bound.

### Changed

- Course list in GUI shows approximate size (MiB) next to each name.
- GUI progress bars apply only the latest queued update per UI drain tick (less flicker under bursty FFmpeg stats).

### Fixed

- GUI error dialog no longer crashes with `NameError` on `exc` (Python 3.12 clears except-bound names before delayed `after` callbacks).

## [0.1.1] — 2026-07-24

### Fixed

- AV1 sample encode no longer fails on MPEG-TS (`.ts`) sources: samples run **video-only** (`-an`) so the size race is not broken by AAC mux into Matroska after input seek.
- When copying AAC from MPEG-TS into MP4/MKV on full encode, apply `aac_adtstoasc`.

### Changed

- User guides note that sample race is video-only.

## [0.1.0] — 2026-07-24

### Added

- Course pipeline `inbox → tmp → outbox` (ADR-0001) with optional `course.json` (ADR-0002).
- HEVC vs AV1 NVENC sample race + min-savings gate (size@CQ disclaimer, no VMAF).
- CLI: `smart-convert`, `smart-convert-course`; GUI: `smart-convert-gui` (CustomTkinter).
- Hard Stop (`taskkill /T` on Windows), unique temp files, hwaccel retry, environment validation.
- Skip videos already in HEVC/AV1; session freed MiB / % / MiB/h in GUI.
- Windows sleep / pending-reboot guard while a job runs.
- Pass-through for courses without video.
- pytest suite with ≥90% coverage (GPU not required).
- GitHub Actions CI + PyInstaller release workflow (`v*` tags).
- MIT license; bilingual docs (EN/RU).

[Unreleased]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AndreyTokarev/smart_convert_nvenc/releases/tag/v0.1.0
