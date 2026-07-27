# Журнал изменений

Все заметные изменения проекта фиксируются в этом файле.

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [Semantic Versioning](https://semver.org/lang/ru/).

English: [CHANGELOG.md](./CHANGELOG.md).

## [Unreleased]

### Added

### Changed

### Fixed

- CI: моки VMAF/ffmpeg в unit-тестах без системного FFmpeg; omit разбитых `gui_*.py` из coverage (как для `gui.py`).

### Removed

## [0.1.11] — 2026-07-27

### Fixed

- Курс больше не падает на одном битом видео (например MP4 без `moov`): оригинал сохраняется, обработка идёт дальше. В ошибках probe виден stderr ffprobe (`-v error`).

## [0.1.10] — 2026-07-26

### Fixed

- Полный encode больше не вешает `aac_adtstoasc` при copy не-AAC из `.mpg`/MPEG-TS (например mp2) — только если probe показал AAC.

## [0.1.9] — 2026-07-26

### Added

- План оставшейся работы (R1–R3): [docs/ru/remaining-work-plan.md](docs/ru/remaining-work-plan.md) · [docs/en/remaining-work-plan.md](docs/en/remaining-work-plan.md). Включает гейт R1.0 (разбиение GUI), единый `course_meta` и seed профиля как у CLI (после thermo-nuclear review).
- R1.0: GUI разбит на `gui_theme` / `gui_layout` / `gui_course_list` / `gui_job` / `gui_paths` (`gui.py` — тонкая оболочка).
- R1.1–R1.4: `course_meta.py` (ADR-0002); title из course.json в GUI и session-report; выбор профиля в GUI через `get_profile → to_convert_settings`; дубликаты по JSON title (+ пересечение publishers).
- R2.1: `--sample-fragments N` — усреднение размера/VMAF по N клипам (один path для N=1).
- R2.2: опциональный NVENC `--nvenc-multipass` / `--nvenc-lookahead` (выкл. по умолчанию).
- R3.1: опциональный `--log-file` через `log_sink.py`.
- R3.2: smoke-скрипт `scripts/smoke_nvenc.py` (не CI).

### Changed

- Гигиена refactoring-plan: сделанные Phase 0–4 + ядро Phase 5 отмечены; smoke/file-logs Phase 5 явно отложены в R3; заголовок решений `3C`; Phase B same-volume отмечен; ARCHITECTURE/USER_GUIDE ссылаются на remaining-work-plan без дублирования чеклиста.
- Документация: CQ≠CRF для GPU vs CPU; в RELEASES чеклист R3.3 (формулировка «неподдерживаемые» пока остаётся).

## [0.1.8] — 2026-07-26

### Added

- Гибридный VMAF для sample race (`--vmaf off|auto|on`, `--vmaf-min`, меню VMAF в GUI): при наличии libvmaf выбираем среди кодеков с VMAF ≥ порога меньший размер; иначе size@CQ.

### Changed

- Документация приведена к текущему продукту (USER_GUIDE, ARCHITECTURE, RELEASES, refactoring-plan, индекс docs): гибридный VMAF, режимы энкодера, профили, дубликаты, overwrite outbox, четыре entry point из исходников.

## [0.1.7] — 2026-07-26

### Added

- Именованные пресеты в `profiles.toml` (`default`, `course`) и CLI `--profile` (флаги перекрывают).
- Локальный helper сборки `scripts/build.ps1` и `docs/*/BUILD.md`.
- Поиск дубликатов (только отчёт): `smart-convert duplicates` / `smart-convert-duplicates` — точные копии файлов (size+SHA-256) и одинаковые имена курсов в inbox/outbox.
- Batch курсов пишет `session-report.md` (итоги + таблица); `--session-report PATH` / `--no-session-report`.
- По умолчанию перезапись существующего `outbox/<course>` (чекбокс GUI + `--overwrite-outbox` / `--no-overwrite-outbox`).

### Fixed

- Игнор macOS AppleDouble `._*` (и похожего junk) — не считаем их видео для encode.

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

[Unreleased]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.11...HEAD
[0.1.11]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/AndreyTokarev/smart_convert_nvenc/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/AndreyTokarev/smart_convert_nvenc/releases/tag/v0.1.0
