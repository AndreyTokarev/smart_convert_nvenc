# smart_convert_nvenc

Сжимает архив **видеокурсов** через NVIDIA NVENC: на коротком сэмпле сравнивает HEVC и AV1, и если прогноз экономии достаточный — кодирует весь файл.

> MVP: один файл, CLI, без VMAF (сравнение size@CQ + дисклеймер). GUI / batch / дубликаты — позже. См. [docs/refactoring-plan.md](docs/refactoring-plan.md).

## Требования

- Windows + Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- FFmpeg с `hevc_nvenc` и `av1_nvenc` (RTX 40xx для AV1 encode)
- NVIDIA-драйвер

Проверка энкодеров:

```powershell
ffmpeg -hide_banner -encoders | findstr nvenc
```

## Course folders (defaults)

```text
courses/inbox/    ← source courses (one folder per course)
courses/tmp/      ← temporary encodes
courses/outbox/   ← result
```

Also keep the machine awake and discourage Windows Update reboots while a job runs
(`shutdown /a` + sleep block; GUI also registers a shutdown block reason).

### Process a course

```powershell
# GUI
uv run smart-convert-gui

# CLI: all courses in inbox
uv run smart-convert-course

# CLI: one course by folder name
uv run smart-convert-course "[0000] Balance (full breakdown) [Jam Track Central] [Olly Steele]"
```

## Установка

```powershell
cd D:\projects\smart_convert_nvenc
uv sync
```

## Запуск

```powershell
uv run smart-convert "D:\path\to\lesson.mp4"
```

Полезные флаги:

```powershell
# только тест сэмпла
uv run smart-convert lesson.mp4 --dry-run

# сильнее жать / другой пресет
uv run smart-convert lesson.mp4 --cq-hevc 30 --cq-av1 34 --preset p7

# перекодировать речь в Opus 96k (по умолчанию звук copy)
uv run smart-convert lesson.mp4 --audio opus:96

# полный encode только если экономия ≥ 15%
uv run smart-convert lesson.mp4 --min-savings 0.15
```

Итог: рядом с исходником появится `*_nvenc_hevc.mp4` или `*_nvenc_av1.mkv`. Исходник не удаляется.

## Документация

- [docs/README.md](docs/README.md)
- [docs/refactoring-plan.md](docs/refactoring-plan.md) — решения 1B / 2C / 3A / 4C
