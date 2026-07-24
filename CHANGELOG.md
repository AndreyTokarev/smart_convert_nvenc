# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Русский: [CHANGELOG.ru.md](./CHANGELOG.ru.md).

## [Unreleased]

### Added

- Queue ordering by size: videos inside a course and courses in CLI/GUI run largest-first so freed space shows up sooner.
- FFmpeg `speed=` shown in the GUI file progress line (e.g. `encode 45% 12.9x`).

### Changed

- Course list in GUI shows approximate size (MiB) next to each name.

### Fixed

### Removed

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

[Unreleased]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AndreyTokarev/smart_convert_nvenc/releases/tag/v0.1.0
