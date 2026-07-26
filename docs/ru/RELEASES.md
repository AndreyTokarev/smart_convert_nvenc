# Релизы / standalone-сборки

English: [../en/RELEASES.md](../en/RELEASES.md).

## Статус (ранний проект)

**Бинарные релизы экспериментальные и пока по сути не тестируются.**  
Проект в самом начале: **рабочий / поддерживаемый** способ запуска — **из исходников** (`git clone` + `uv sync` + `uv run …`).  
Zip в GitHub Releases — задел на будущее; считайте их **неподдерживаемыми / на свой риск**, пока эта пометка не снята.

### Чеклист планки поддержки (R3.3 — до снятия «неподдерживаемых»)

- [ ] Мейнтейнер: `uv run python scripts/smoke_nvenc.py --encode` на Windows + NVIDIA (драйвер ок для bundled FFmpeg n8.1)
- [ ] Smoke: encode одного файла и короткий course dry-run из release zip (или из исходников с тем же FFmpeg)
- [ ] Записать дату / GPU / драйвер / сборку FFmpeg в этот раздел
- [ ] Затем смягчить или убрать формулировку «неподдерживаемые» выше

## Что лежит в GitHub Releases

На каждый git-тег `v*` (например `v0.1.11`) workflow [`.github/workflows/release.yml`](../../.github/workflows/release.yml) собирает **PyInstaller** one-file бинарники:

| Архив | Runner | Примечание |
|-------|--------|------------|
| `smart_convert_nvenc-windows-amd64.zip` | `windows-latest` | `.exe` CLI + GUI |
| `smart_convert_nvenc-linux-amd64.zip` | `ubuntu-latest` | ELF |
| `smart_convert_nvenc-macos-arm64.zip` | `macos-latest` | Apple Silicon (текущие runners GitHub) |

В каждом zip:

- **`smart-convert`** — один бинарник: GUI (по умолчанию) / `course …` / `duplicates …` / один файл
- `README` / `LICENSE` / `README-RELEASE.txt`
- **Windows / Linux:** также `ffmpeg/bin/ffmpeg` + `ffprobe` (BtbN GPL **n8.1** static с **`hevc_nvenc` + `av1_nvenc`**, с тега `latest` — не bleeding-edge `master`, который часто требует более новый NVENC API драйвера)
- **macOS:** FFmpeg **не** кладётся в архив (у BtbN нет macOS-артефактов)

## Почему четыре команды из исходников / почему раньше в zip было три exe

У приложения **четыре задачи** (из исходников) / один лаунчер в релизе:

| Задача | Из исходников (`uv`) | Zip релиза (с v0.1.4) |
|--------|----------------------|------------------------|
| Один видеофайл | `uv run smart-convert …` | `smart-convert video.mp4 …` |
| Курсы inbox→outbox | `uv run smart-convert-course …` | `smart-convert course …` |
| Отчёт о дубликатах | `uv run smart-convert-duplicates …` | `smart-convert duplicates …` |
| GUI | `uv run smart-convert-gui` | `smart-convert` / `smart-convert gui` |

Это четыре `[project.scripts]` в `pyproject.toml` (`cli`, `course_cli`, `duplicates_cli`, `gui`). Так удобнее при разработке через `uv`: CLI не тащит GUI-стек без нужды.

**До v0.1.3 включительно** release zip повторял CLI/course/GUI 1:1 — PyInstaller собирал **три** one-file бинарника. Один и тот же код, три обёртки; zip выглядел перегруженным и почти утраивал размер без пользы для пользователя.

**С v0.1.4** в zip один `smart-convert` с лаунчером по argv (GUI по умолчанию; `duplicates` — в более поздних тегах). Четыре команды `uv run …` для запуска из исходников **остаются**.

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
git tag v0.1.11
git push origin v0.1.11
```

Либо вручную Actions → **Release** → Run workflow.

CLI/GUI показывают ту же версию: `smart-convert --version` / заголовок окна.

## Локальная сборка

```powershell
uv sync --group release
uv run pyinstaller --noconfirm --clean --onefile --name smart-convert `
  --collect-all customtkinter --collect-data smart_convert_nvenc `
  scripts/pyi_smart_convert.py
```

Или: `scripts/build.ps1` (−WithFfmpeg опционально). См. [BUILD.md](./BUILD.md).

Артефакты — в `dist/`. Опционально: `scripts/fetch_ffmpeg.sh windows-amd64 dist/smart_convert_nvenc-windows-amd64`.
