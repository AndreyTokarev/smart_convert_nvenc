# smart_convert_nvenc

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.9-blue.svg)](CHANGELOG.ru.md)

**[English](README.md)** · **[Русский](README.ru.md)**

Сжимает **архивы видеокурсов** через **NVIDIA NVENC**: на коротком сэмпле сравнивает HEVC и AV1, полный encode только если есть экономия места, решение на уровне **папки курса** (`inbox → tmp → outbox`).

Быстрый личный MVP, теперь open source под **MIT**.

Текущая версия: **0.1.9** — [CHANGELOG.ru.md](CHANGELOG.ru.md) · [CHANGELOG.md](CHANGELOG.md).

| Язык | Документация |
|------|--------------|
| **English** | [USER_GUIDE](docs/en/USER_GUIDE.md) · [ARCHITECTURE](docs/en/ARCHITECTURE.md) · [RELEASES](docs/en/RELEASES.md) · [BUILD](docs/en/BUILD.md) · [ADRs](docs/en/adr/README.md) |
| **Русский** | [руководство](docs/ru/USER_GUIDE.md) · [архитектура](docs/ru/ARCHITECTURE.md) · [релизы](docs/ru/RELEASES.md) · [сборка](docs/ru/BUILD.md) · [ADR](docs/ru/adr/README.md) |

Полный индекс: [docs/README.md](docs/README.md).

## Зачем

Онлайн-курсы (экран + слайды + речь) съедают диск. Киношное качество обычно не нужно — нужны **читаемые слайды**, **разборчивый звук** и **место** под следующую загрузку. Инструмент пакетно сжимает целые деревья курсов на GPU NVIDIA (или CPU-энкодерах по выбору).

## Возможности

- **Sample race** HEVC vs AV1 + порог экономии; опциональный **гибридный VMAF**, если в FFmpeg есть `libvmaf` (`--vmaf auto|off|on`)
- Конвейер курса: не-видео сохраняются; невыгодные курсы уходят как есть
- Именованные **профили** (`default` / `course`) через `--profile`
- Режимы энкодера: **gpu** / **cpu** / **auto**
- **Отчёт** о дубликатах (без удаления): `smart-convert duplicates`
- Перезапись существующих курсов в outbox по умолчанию
- Markdown-отчёт сессии после пачки (`session-report.md`)
- CLI + **GUI** CustomTkinter (пути, очередь, логи, freed MiB / % / MiB/h)
- Жёсткий **Stop**, уникальные temp, retry без hwaccel, Windows sleep/reboot guard
- Тесты с покрытием **≥90%** (GPU для CI не нужен)

## Требования

- Windows 10/11 + Python 3.12+ (основная цель; есть сборки Linux/macOS)
- [uv](https://github.com/astral-sh/uv)
- FFmpeg:
  - **GPU (по умолчанию):** нужен `hevc_nvenc`; `av1_nvenc` опционален (иначе AV1 через **libsvtav1**)
  - **CPU / auto:** `libx265` + `libsvtav1`
- Драйвер NVIDIA при режиме GPU (RTX 40xx для аппаратного AV1)

```powershell
ffmpeg -hide_banner -encoders | findstr /i "nvenc libx265 libsvtav1"
```

## Быстрый старт

```powershell
git clone https://github.com/AndreyTokarev/smart_convert_nvenc.git
cd smart_convert_nvenc
uv sync

uv run smart-convert-gui
uv run smart-convert-course --profile course
uv run smart-convert "D:\path\to\lesson.mp4" --vmaf auto
uv run smart-convert-duplicates
```

Раскладка по умолчанию:

```text
courses/inbox/   ← сюда папки курсов
courses/tmp/     ← рабочая зона encode
courses/outbox/  ← результат
```

## Релизы (standalone)

Тег `v*` → GitHub Actions собирает zip для Windows / Linux / macOS (PyInstaller).  
**Ранний проект:** бинарные релизы **экспериментальные**; предпочитайте **исходники**.  
**Один бинарник** `smart-convert` (GUI / `course` / `duplicates` / файл). Win/Linux — FFmpeg **n8.1** в `ffmpeg/bin/`. Подробнее: [docs/ru/RELEASES.md](docs/ru/RELEASES.md) · [docs/ru/BUILD.md](docs/ru/BUILD.md).

## Лицензия

[MIT](LICENSE) — можно использовать, менять и распространять.

## Автор

Andrey Tokarev — [GitHub](https://github.com/AndreyTokarev)
