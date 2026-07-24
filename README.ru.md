# smart_convert_nvenc

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.6-blue.svg)](CHANGELOG.ru.md)

**[English](README.md)** · **[Русский](README.ru.md)**

Сжимает **архивы видеокурсов** через **NVIDIA NVENC**: на коротком сэмпле сравнивает HEVC и AV1, полный encode только если есть экономия места, решение на уровне **папки курса** (`inbox → tmp → outbox`).

Быстрый личный MVP, теперь open source под **MIT**.

Текущая версия: **0.1.6** — [CHANGELOG.ru.md](CHANGELOG.ru.md) · [CHANGELOG.md](CHANGELOG.md).

| Язык | Документация |
|------|--------------|
| **English** | [USER_GUIDE](docs/en/USER_GUIDE.md) · [ARCHITECTURE](docs/en/ARCHITECTURE.md) · [RELEASES](docs/en/RELEASES.md) · [refactoring plan](docs/en/refactoring-plan.md) · [ADRs](docs/en/adr/README.md) |
| **Русский** | [руководство](docs/ru/USER_GUIDE.md) · [архитектура](docs/ru/ARCHITECTURE.md) · [релизы](docs/ru/RELEASES.md) · [план рефакторинга](docs/ru/refactoring-plan.md) · [ADR](docs/ru/adr/README.md) |

Полный индекс: [docs/README.md](docs/README.md).

## Зачем

Онлайн-курсы (экран + слайды + речь) съедают диск. Киношное качество обычно не нужно — нужны **читаемые слайды**, **разборчивый звук** и **место** под следующую загрузку. Инструмент пакетно сжимает целые деревья курсов на GPU NVIDIA.

## Возможности

- **Sample race** HEVC vs AV1 + порог экономии (честный дисклеймер size@CQ, без VMAF в MVP)
- Конвейер курса: не-видео сохраняются; невыгодные курсы уходят как есть
- CLI + **GUI** на CustomTkinter (на весь экран, выбор путей, freed MiB / % / MiB/h за сессию)
- Жёсткий **Stop** (убийство дерева процессов на Windows), уникальные temp, retry без hwaccel
- Пропуск уже HEVC/AV1
- Блокировка сна / отмена отложенной перезагрузки Windows на время job
- Тесты с покрытием **≥90%** (GPU для CI не нужен)

## Требования

- Windows 10/11 + Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- FFmpeg с `hevc_nvenc` + `av1_nvenc` (RTX 40xx для AV1 encode)
- Драйвер NVIDIA

```powershell
ffmpeg -hide_banner -encoders | findstr nvenc
```

## Быстрый старт

```powershell
git clone https://github.com/AndreyTokarev/smart_convert_nvenc.git
cd smart_convert_nvenc
uv sync

# GUI
uv run smart-convert-gui

# или CLI: все курсы в courses/inbox
uv run smart-convert-course

# один файл
uv run smart-convert "D:\path\to\lesson.mp4"
```

Раскладка по умолчанию:

```text
courses/inbox/   ← сюда папки курсов
courses/tmp/     ← рабочая зона encode
courses/outbox/  ← результат
```

## Релизы (standalone)

Тег `v*` → GitHub Actions собирает zip для Windows / Linux / macOS (PyInstaller).  
**Ранний проект:** бинарные релизы **экспериментальные и по сути не тестируются**; **рабочий** способ — **из исходников** (`uv sync` / `uv run`). Zip — на свой риск.  
**Один бинарник** `smart-convert` (GUI / `course` / файл). В **Win/Linux** — FFmpeg n8.1 в `ffmpeg/bin/`; **macOS** — ставьте FFmpeg сами. Для NVENC нужен драйвер NVIDIA. Подробнее: [docs/ru/RELEASES.md](docs/ru/RELEASES.md) · [docs/en/RELEASES.md](docs/en/RELEASES.md).

## Лицензия

[MIT](LICENSE) — можно использовать, менять и распространять.

## Ещё документация

- Журнал изменений: [CHANGELOG.ru.md](CHANGELOG.ru.md) · [CHANGELOG.md](CHANGELOG.md)
- Индекс: [docs/README.md](docs/README.md)
- Решения по продукту: [RU](docs/ru/refactoring-plan.md) · [EN](docs/en/refactoring-plan.md)
- План переноса фич: [RU](docs/ru/feature-port-plan.md) · [EN](docs/en/feature-port-plan.md)
- ADR: [RU](docs/ru/adr/) · [EN](docs/en/adr/)
