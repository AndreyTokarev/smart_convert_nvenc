# Журнал изменений

Все заметные изменения проекта фиксируются в этом файле.

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [Semantic Versioning](https://semver.org/lang/ru/).

English: [CHANGELOG.md](./CHANGELOG.md).

## [Unreleased]

### Added

- Именованные пресеты в `profiles.toml` (`default`, `course`) и CLI `--profile` (флаги перекрывают).
- Локальный helper сборки `scripts/build.ps1` и `docs/*/BUILD.md`.
- Поиск дубликатов (только отчёт): `smart-convert duplicates` / `smart-convert-duplicates` — точные копии файлов (size+SHA-256) и одинаковые имена курсов в inbox/outbox.
- Batch курсов пишет `session-report.md` (итоги + таблица); `--session-report PATH` / `--no-session-report`.
- По умолчанию перезапись существующего `outbox/<course>` (чекбокс GUI + `--overwrite-outbox` / `--no-overwrite-outbox`).

### Changed

### Fixed

### Removed

## [0.1.6] — 2026-07-25

### Changed

- В zip кладётся BtbN **n8.1** FFmpeg (**`hevc_nvenc` + `av1_nvenc`**). Проверено на актуальных драйверах NVIDIA; libsvtav1 остаётся fallback, если `av1_nvenc` нет.

## [0.1.5] — 2026-07-25

### Fixed

- Режим gpu больше не требует `av1_nvenc`. В bundled FFmpeg n7.1 был только HEVC NVENC; если `av1_nvenc` нет, race/encode AV1 идёт через **libsvtav1** (CPU) — AV1 остаётся доступен.
- Старт GUI больше не врёт «NVENC недоступен» на сборках только с `hevc_nvenc`.

## [0.1.4] — 2026-07-25

### Added

- Один бинарник релиза `smart-convert`: GUI (по умолчанию), `course …` или один видеофайл.

### Changed

- В zip кладётся BtbN **n7.1** FFmpeg (не `master`), чтобы NVENC работал на чуть более старых драйверах.
- Флаги AQ NVENC: `-spatial-aq` / `-temporal-aq` (как требует свежий FFmpeg).

### Fixed

- В ошибках FFmpeg теперь хвост лога (видны сообщения про драйвер/NVENC).

## [0.1.3] — 2026-07-25

### Added

- Режим энкодера `gpu` (по умолчанию) / `cpu` / `auto`: принудительно libx265 + libsvtav1 или auto-fallback без NVENC (`--encoder`, меню Encoder в GUI).
- В Win/Linux release zip кладётся FFmpeg BtbN GPL в `ffmpeg/bin/` (latest на момент сборки); приложение предпочитает bundled поверх PATH (`SMART_CONVERT_FFMPEG_DIR`).

### Changed

- В документации явно: standalone-бинарники ранние/экспериментальные; поддерживаемый путь — из исходников.

### Fixed

- Сборка PyInstaller (GUI/CLI) больше не требует `pyproject.toml`; по умолчанию `courses/` создаётся рядом с exe.

## [0.1.2] — 2026-07-25

### Added

- Очередь по размеру: видео внутри курса и курсы в CLI/GUI — сначала самые крупные, чтобы быстрее видеть freed space.
- В строке прогресса GUI показывается FFmpeg `speed=` (например `encode 45% 12.9x`).
- Ring-buffer логов GUI (app 2000 / FFmpeg 1000 строк), чтобы overnight-прогон не раздувал Textbox.

### Changed

- В списке курсов GUI рядом с именем показывается примерный размер (MiB).
- Progress bar в GUI применяет только последний апдейт за тик drain (меньше дёрганья при частых stats FFmpeg).

### Fixed

- Диалог ошибки GUI больше не падает с `NameError` на `exc` (в Python 3.12 имя из `except` очищается до отложенного `after`).

## [0.1.1] — 2026-07-24

### Fixed

- Sample encode AV1 больше не падает на MPEG-TS (`.ts`): сэмплы идут **только с видео** (`-an`), чтобы race по размеру не ломался из‑за mux AAC в Matroska после seek.
- При полном encode с copy AAC из MPEG-TS в MP4/MKV применяется `aac_adtstoasc`.

### Changed

- В руководствах указано, что sample race — только видео.

## [0.1.0] — 2026-07-24

### Added

- Конвейер курса `inbox → tmp → outbox` (ADR-0001) и опциональный `course.json` (ADR-0002).
- Sample race HEVC vs AV1 NVENC + порог экономии (дисклеймер size@CQ, без VMAF).
- CLI: `smart-convert`, `smart-convert-course`; GUI: `smart-convert-gui` (CustomTkinter).
- Жёсткий Stop (`taskkill /T` на Windows), уникальные temp, retry без hwaccel, проверка окружения.
- Пропуск уже HEVC/AV1; в GUI — freed MiB / % / MiB/h за сессию.
- Блокировка сна / отмена отложенной перезагрузки Windows на время job.
- Pass-through курсов без видео.
- pytest с покрытием ≥90% (GPU для CI не нужен).
- GitHub Actions CI + PyInstaller release (`v*` теги).
- MIT; документация на русском и английском.

[Unreleased]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.6...HEAD
[0.1.6]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AndreyTokarev/smart_convert_nvenc/releases/tag/v0.1.0
