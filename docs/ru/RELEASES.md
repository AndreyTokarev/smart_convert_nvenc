# Релизы / standalone-сборки

English: [../en/RELEASES.md](../en/RELEASES.md).

## Что лежит в GitHub Releases

На каждый git-тег `v*` (например `v0.1.0`) workflow [`.github/workflows/release.yml`](../../.github/workflows/release.yml) собирает **PyInstaller** one-file бинарники:

| Архив | Runner | Примечание |
|-------|--------|------------|
| `smart_convert_nvenc-windows-amd64.zip` | `windows-latest` | `.exe` CLI + GUI |
| `smart_convert_nvenc-linux-amd64.zip` | `ubuntu-latest` | ELF |
| `smart_convert_nvenc-macos-arm64.zip` | `macos-latest` | Apple Silicon (текущие runners GitHub) |

В каждом zip: `smart-convert`, `smart-convert-course`, `smart-convert-gui`, плюс `README` / `LICENSE` / `README-RELEASE.txt`.

## Важно: FFmpeg всё равно нужен

Сборки **не** включают FFmpeg и драйверы NVIDIA.

На машине по-прежнему нужны:

1. FFmpeg с `hevc_nvenc` + `av1_nvenc` в `PATH`
2. GPU NVIDIA + драйвер для реального NVENC

Сборки под macOS/Linux нужны для удобного запуска приложения, но **encode через NVENC — про NVIDIA**. Без подходящего FFmpeg/GPU проверка окружения упадёт.

## Как выпустить релиз

```powershell
git tag v0.1.0
git push origin v0.1.0
```

Либо вручную Actions → **Release** → Run workflow.

## Локальная сборка

```powershell
uv sync --group release
uv run pyinstaller --onefile --name smart-convert scripts/pyi_smart_convert.py
uv run pyinstaller --onefile --name smart-convert-course scripts/pyi_smart_convert_course.py
uv run pyinstaller --onefile --windowed --collect-all customtkinter --name smart-convert-gui scripts/pyi_smart_convert_gui.py
```

Артефакты — в `dist/`.
