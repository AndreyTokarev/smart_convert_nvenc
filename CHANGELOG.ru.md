# Журнал изменений

Все заметные изменения проекта фиксируются в этом файле.

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [Semantic Versioning](https://semver.org/lang/ru/).

English: [CHANGELOG.md](./CHANGELOG.md).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

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

[Unreleased]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AndreyTokarev/smart_convert_nvenc/releases/tag/v0.1.0
