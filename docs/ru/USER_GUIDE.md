# Руководство пользователя — smart_convert_nvenc

Подробная документация на русском. English: [../en/USER_GUIDE.md](../en/USER_GUIDE.md).

## 1. Зачем этот проект

Личный (и теперь открытый) инструмент для **освобождения места на диске** от большого архива **видеокурсов**: записи экрана, слайды, речь.

Типичная боль:

- курсы весят сотни гигабайт / терабайты;
- исходники часто в «жирном» H.264 или бездумно снятом bitrate;
- для обучения достаточно читаемых слайдов и разборчивой речи — не кинотеатральный Blu-ray;
- нужно обрабатывать **папки курсов целиком** (видео + PDF + табы + mp3), а не один файл.

**smart_convert_nvenc** сжимает видео через **NVIDIA NVENC** (аппаратный encode), решает на уровне **курса**, переносит результат в outbox и старается не раздувать диск временными копиями.

Проект написан **с нуля** (быстрый MVP), опираясь на опыт предыдущего личного сервиса, но с другой продуктовой моделью: не in-place замена файлов, а конвейер `inbox → tmp → outbox`.

Лицензия: **MIT** — можно использовать, менять, распространять.

## 2. Что умеет (сейчас)

| Возможность | Описание |
|-------------|----------|
| Sample race HEVC vs AV1 | На коротком фрагменте сравнивает размер при заданных CQ; победитель идёт в полный encode |
| Порог экономии | Не держит сжатый файл / курс, если выигрыш меньше порога |
| Конвейер курса | Первая папка в inbox = один курс; не-видео сохраняются |
| CLI файла | `smart-convert` — один файл |
| CLI курса | `smart-convert-course` — inbox/outbox |
| GUI | Очередь курсов, пути, логи, progress, экономия сессии |
| Hard Stop | Убивает дерево процессов FFmpeg (`taskkill /T`) |
| Skip same codec | Не перекодирует уже HEVC/AV1 (настраивается) |
| Pass-through без видео | Курс только с PDF и т.п. → сразу в outbox |
| Windows guard | Блокирует sleep, периодически `shutdown /a` |
| Сохранение настроек GUI | `%APPDATA%\smart_convert_nvenc\settings.json` |
| Тесты | `pytest` + coverage ≥ 90% (без GPU) |

## 3. Чего нет (намеренно / пока)

- VMAF / «равное качество» при сравнении кодеков (есть дисклеймер size@CQ)
- Автопереименование папок курсов
- Поиск дубликатов (в планах)
- Готовый `.exe` installer (в планах)
- Аппаратный encode AMD/Intel; перекалибровка CQ↔CRF для CPU vs NVENC

## 4. Требования

- **ОС:** Windows 10/11 (основная цель; пути и guard заточены под Win)
- **Python:** 3.12+
- **Пакетный менеджер:** [uv](https://github.com/astral-sh/uv)
- **FFmpeg** в `PATH` (при запуске из исходников):
  - **GPU (по умолчанию):** `hevc_nvenc` и `av1_nvenc`
  - **CPU / auto-fallback:** `libx265` и `libsvtav1`
  - В Win/Linux release zip FFmpeg уже лежит в `ffmpeg/bin/`; опционально: `SMART_CONVERT_FFMPEG_DIR`
- **GPU (опционально):** NVIDIA с NVENC; для **AV1 encode** обычно RTX 40xx
- Драйвер NVIDIA актуальной ветки (при режиме GPU)

Проверка:

```powershell
ffmpeg -hide_banner -encoders | findstr /i "nvenc libx265 libsvtav1"
ffprobe -version
```

## 5. Установка

**Поддерживаемый путь:** клонировать репозиторий и запускать через `uv` (из исходников). Zip из GitHub Releases есть, но это **ранний / непротестированный** вариант — см. [RELEASES.md](./RELEASES.md).

```powershell
git clone https://github.com/AndreyTokarev/smart_convert_nvenc.git
cd smart_convert_nvenc
uv sync
# для разработки / тестов:
uv sync --group dev
```

Точки входа после sync:

| Команда | Назначение |
|---------|------------|
| `uv run smart-convert` | Один видеофайл |
| `uv run smart-convert-course` | Курсы из inbox |
| `uv run smart-convert-gui` | Графический интерфейс |

Три скрипта — для запуска из исходников; в **release zip** один `smart-convert` с теми же режимами — см. [RELEASES.md](./RELEASES.md) («Почему три команды…»).

## 6. Модель папок (ADR-0001)

По умолчанию рядом с репозиторием:

```text
courses/
  inbox/     ← положить папки курсов
  tmp/       ← временные encode (чистится)
  outbox/    ← результат (сжатый или исходник as-is)
```

**Единица работы** — папка первого уровня в `inbox/`.

Алгоритм для курса:

1. Посчитать размер всего дерева.
2. Для каждого видео: sample race (или force codec) → полный encode в `tmp/<course>/…` при достаточной экономии.
3. Собрать кандидатный размер (сжатые видео + все не-видео).
4. Если курс выгоден → собрать дерево в `outbox` (видео из tmp, остальное move из inbox).
5. Если невыгоден → `move inbox/Name → outbox/Name`.
6. При ошибке mid-flight: курс остаётся в inbox; частичный outbox не публикуется.

Переопределение путей:

- CLI: `--courses-root`, `--inbox`, `--outbox`, `--tmp`
- Env: `SMART_CONVERT_COURSES_ROOT`, `SMART_CONVERT_INBOX`, `SMART_CONVERT_OUTBOX`, `SMART_CONVERT_TMP`
- GUI: панель Folders + сохранение в settings.json

Рекомендация: inbox/outbox/tmp на **одном томе**, чтобы `move` не превращался в copy+delete.

## 7. Именование курсов и метаданные (ADR-0002)

**Целевое** короткое имя папки:

```text
[0000] 20 Sick Licks
[2024] Complete Jazz Guitar
```

`[0000]` = год неизвестен. Издателя/автора **не** тащить в путь (MAX_PATH).

Опционально в корне курса файл `course.json`:

```json
{
  "schema": 1,
  "title": "20 Sick Licks",
  "year": null,
  "publishers": ["Jam Track Central"],
  "authors": ["Matteo Mancuso"],
  "notes": ""
}
```

Сейчас encode **не требует** JSON; файл просто переносится с курсом. Позже — маркер корня и метаданные для отчётов/дубликатов.

Любые имена папок валидны: инструмент **не переименовывает**.

## 8. Как выбирается кодек

1. Берётся сэмпл (по умолчанию ~20–30 с, со смещением ~25% длительности).
2. Кодируется HEVC (CQ по умолчанию 28) и AV1 (CQ 32) на сэмпле **только видео** (`-an`), чтобы race по размеру не искажался аудио и seek по MPEG-TS не ломал mux.
   - Режим gpu: HEVC через `hevc_nvenc`. AV1 — `av1_nvenc`, если есть (в bundled n8.1 есть); иначе fallback **libsvtav1** (CPU).
3. Меньший сэмпл → победитель; размер проецируется на полную длительность.
4. Если прогнозная экономия < `min_savings` → skip полного encode файла.
5. После полного encode повторная проверка фактического размера.
6. На уровне курса — суммарный порог `min_course_savings`.

**Дисклеймер:** сравнение size@разных CQ — **не** равное качество. Для курсов со слайдами обычно достаточно; VMAF в MVP нет.

По умолчанию **race once** на курс: победитель первого сжатого видео фиксируется для остальных (быстрее).

Аудио финального файла по умолчанию **`copy`**. Можно `--audio aac:128` / `opus:96`.

## 9. GUI

```powershell
uv run smart-convert-gui
```

Окно стартует **развёрнутым**.

Основные блоки:

- **Folders** — inbox/outbox/tmp, Browse, Courses root, Apply, Defaults
- **Courses** — список, Refresh / Select all / Open inbox|outbox
- **Settings** — sample, min savings, CQ, preset, codec, encoder (gpu/cpu/auto), Skip if already HEVC/AV1
- **Progress** — file/job bars + Last / Session freed / % · MiB/h
- **App log / FFmpeg** — журнал и live-строка ffmpeg

Настройки и пути пишутся в:

`%APPDATA%\smart_convert_nvenc\settings.json`

**Stop** жёстко убивает текущий FFmpeg (не «после файла»).

Режимы энкодера: `gpu` (только NVENC, по умолчанию), `cpu` (libx265 / libsvtav1), `auto` (NVENC если есть, иначе CPU).

Именованные пресеты — в `src/smart_convert_nvenc/data/profiles.toml` (`default`, `course`). Флаг `--profile`; остальные CLI-флаги перекрывают профиль.

## 10. CLI

### Один файл

```powershell
uv run smart-convert lesson.mp4
uv run smart-convert lesson.mp4 --profile course
uv run smart-convert lesson.mp4 --dry-run
uv run smart-convert lesson.mp4 --force-codec hevc --cq-hevc 30
uv run smart-convert lesson.mp4 --encoder auto
uv run smart-convert lesson.mp4 --encoder cpu --force-codec hevc
uv run smart-convert lesson.mp4 --audio opus:96 --min-savings 0.15
uv run smart-convert lesson.mp4 --reencode-same-codec
```

### Курс

```powershell
uv run smart-convert-course
uv run smart-convert-course --profile course
uv run smart-convert-course "My Course Name"
uv run smart-convert-course --encoder auto
uv run smart-convert-course --courses-root E:\archive\courses
uv run smart-convert-course --race-each
uv run smart-convert-course --reencode-same-codec
```

После пачки курсов итоги пишутся в `courses/session-report.md` (`--session-report PATH` / `--no-session-report`).

### Дубликаты (только отчёт)

```powershell
uv run smart-convert duplicates
uv run smart-convert duplicates --videos-only -o dupes.md
uv run smart-convert-duplicates E:\archive\courses\inbox E:\archive\courses\outbox --min-size 0
```

Ищет точные копии файлов (size + SHA-256) и курсы с одинаковым именем. **Ничего не удаляет.**

## 11. Переменные окружения

| Переменная | Смысл |
|------------|--------|
| `SMART_CONVERT_COURSES_ROOT` | Корень с inbox/outbox/tmp |
| `SMART_CONVERT_INBOX` | Путь inbox |
| `SMART_CONVERT_OUTBOX` | Путь outbox |
| `SMART_CONVERT_TMP` | Путь tmp |
| `SMART_CONVERT_APPDATA` | Корень для settings.json (тесты/portable) |
| `SMART_CONVERT_FFMPEG_DIR` | Каталог с `ffmpeg`/`ffprobe` (или `…/bin`); перекрывает bundled + PATH |

## 12. Тесты

```powershell
uv sync --group dev
uv run pytest --cov=smart_convert_nvenc --cov-report=term-missing
```

GPU не нужен: encode/ffprobe мокаются. `gui.py` исключён из метрики покрытия.

## 13. Архитектура модулей (кратко)

См. также [ARCHITECTURE.md](./ARCHITECTURE.md).

| Модуль | Роль |
|--------|------|
| `profiles.py` | Именованные пресеты из `data/profiles.toml` |
| `duplicates.py` | Отчёт: точные копии файлов + одинаковые имена курсов |
| `pipeline.py` | Race + encode одного файла |
| `course.py` | Обход курса, assemble outbox |
| `encode.py` | argv NVENC, temp, retry без hwaccel |
| `ffmpeg_runner.py` | Popen registry, cancel, taskkill |
| `probe.py` | ffprobe + validate_environment |
| `gui.py` / `gui_settings.py` | UI + persist |
| `session.py` | Σ freed / % / MiB/h |
| `windows_guard.py` | sleep / reboot guard |
| `temp_paths.py` | `*.conv.<id>.*` |
| `paths.py` | resolve inbox/outbox/tmp |

## 14. Безопасность и дисклеймеры

- Инструмент **меняет** ваши медиафайлы (перенос/перекодирование). Делайте бэкап критичного архива.
- MIT «AS IS» — без гарантий.
- Не публикуйте чужой контент курсов вместе с репозиторием (gitignore уже исключает media в `courses/`).

## 15. Roadmap (высокоуровнево)

- Позже: VMAF / гибрид

Детали: [feature-port-plan.md](./feature-port-plan.md), [refactoring-plan.md](./refactoring-plan.md).
