# Релизы / standalone-сборки

English: [../en/RELEASES.md](../en/RELEASES.md).

## Статус (ранний проект)

**Бинарные релизы экспериментальные и пока по сути не тестируются.**  
Проект в самом начале: **рабочий / поддерживаемый** способ запуска — **из исходников** (`git clone` + `uv sync` + `uv run …`).  
Zip в GitHub Releases — задел на будущее; считайте их **неподдерживаемыми / на свой риск**, пока эта пометка не снята.

## Что лежит в GitHub Releases

На каждый git-тег `v*` (например `v0.1.0`) workflow [`.github/workflows/release.yml`](../../.github/workflows/release.yml) собирает **PyInstaller** one-file бинарники:

| Архив | Runner | Примечание |
|-------|--------|------------|
| `smart_convert_nvenc-windows-amd64.zip` | `windows-latest` | `.exe` CLI + GUI |
| `smart_convert_nvenc-linux-amd64.zip` | `ubuntu-latest` | ELF |
| `smart_convert_nvenc-macos-arm64.zip` | `macos-latest` | Apple Silicon (текущие runners GitHub) |

В каждом zip: `smart-convert`, `smart-convert-course`, `smart-convert-gui`, плюс `README` / `LICENSE` / `README-RELEASE.txt`.

- **Windows / Linux:** также `ffmpeg/bin/ffmpeg` + `ffprobe` (BtbN GPL **n7.1** static, скачивается при сборке с тега `latest` — не bleeding-edge `master`, который часто требует более новый NVENC API драйвера)
- **macOS:** FFmpeg **не** кладётся в архив (у BtbN нет macOS-артефактов)

## FFmpeg в zip

- В Win/Linux-релизах FFmpeg **включён** в `ffmpeg/bin/`. Приложение предпочитает его PATH (`SMART_CONVERT_FFMPEG_DIR` перекрывает).
- Бинарники FFmpeg — **GPL** (сборка BtbN GPL); см. `ffmpeg/SOURCE.txt` / license в zip.
- **Драйверы NVIDIA не поставляются.** Для NVENC нужны GPU и драйвер на машине.
- **Из исходников** (`uv run`): поставьте FFmpeg сами в `PATH` (или `SMART_CONVERT_FFMPEG_DIR`).

Сборки под macOS/Linux нужны для удобного запуска приложения, но **encode через NVENC — про NVIDIA**. Без подходящего FFmpeg/GPU проверка окружения упадёт.

## Как выпустить релиз

1. Обновить `__version__` в `src/smart_convert_nvenc/__init__.py` (единый источник; hatch читает оттуда).
2. Перенести пункты из **Unreleased** в новую секцию [CHANGELOG.ru.md](../../CHANGELOG.ru.md) и [CHANGELOG.md](../../CHANGELOG.md).
3. Закоммитить и поставить тег, совпадающий с версией:

```powershell
git tag v0.1.2
git push origin v0.1.2
```

Либо вручную Actions → **Release** → Run workflow.

CLI/GUI показывают ту же версию: `smart-convert --version` / заголовок окна.

## Локальная сборка

```powershell
uv sync --group release
uv run pyinstaller --onefile --name smart-convert scripts/pyi_smart_convert.py
uv run pyinstaller --onefile --name smart-convert-course scripts/pyi_smart_convert_course.py
uv run pyinstaller --onefile --windowed --collect-all customtkinter --name smart-convert-gui scripts/pyi_smart_convert_gui.py
```

Артефакты — в `dist/`.
