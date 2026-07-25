# Локальная сборка (standalone binary)

English: [../en/BUILD.md](../en/BUILD.md).

## Поддерживаемый путь

Обычная работа — **из исходников**:

```powershell
uv sync
uv run smart-convert-gui
# или
uv run smart-convert path\to\video.mp4
uv run smart-convert-course --profile course
```

Zip с GitHub Actions — **экспериментальные**. Пока дисклеймер не снят, предпочитайте исходники.

## Локальный Windows exe

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
# опционально: скачать BtbN FFmpeg n8.1 в папку сборки
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -WithFfmpeg
```

Результат: `dist/smart_convert_nvenc-windows-amd64/smart-convert.exe` (+ `ffmpeg/bin/` при `-WithFfmpeg`).

Эквивалент одной командой (как в CI):

```powershell
uv sync --group release
uv run pyinstaller --noconfirm --clean --onefile --name smart-convert `
  --collect-all customtkinter --collect-data smart_convert_nvenc `
  scripts/pyi_smart_convert.py
```

## CI release

Тег `v*` (или `workflow_dispatch`) запускает [`.github/workflows/release.yml`](../../.github/workflows/release.yml): PyInstaller onefile для Windows / Linux / macOS, zip, FFmpeg на Win/Linux через `scripts/fetch_ffmpeg.sh`.

Подробнее: [RELEASES.md](./RELEASES.md).

## Профили в бинарнике

Именованные пресеты — `smart_convert_nvenc/data/profiles.toml`. Для frozen exe нужен `--collect-data smart_convert_nvenc`, иначе `--profile` не найдёт файл.
