# Архитектура — smart_convert_nvenc

English: [../en/ARCHITECTURE.md](../en/ARCHITECTURE.md).

## Цель системы

Сжать архив видеокурсов с помощью NVIDIA NVENC так, чтобы:

1. экономить место при приемлемом качестве для слайдов+речи;
2. работать единицами **курс** (папка), а не разрозненными файлами;
3. не портить inbox частичными результатами;
4. не дублировать весь курс на диск во время работы.

## Потоки данных

```text
                    ┌─────────────┐
   course folder →  │ courses/    │
                    │  inbox/     │
                    └──────┬──────┘
                           │ list + probe + encode
                           ▼
                    ┌─────────────┐
                    │ courses/    │
                    │  tmp/       │  unique *.conv.<id>.* then promote
                    └──────┬──────┘
                           │ assemble OR pass-through original
                           ▼
                    ┌─────────────┐
                    │ courses/    │
                    │  outbox/    │
                    └─────────────┘
```

Решения зафиксированы в ADR:

- [ADR-0001](../adr/0001-course-inbox-outbox-tmp.md) — конвейер папок
- [ADR-0002](../adr/0002-course-folder-naming.md) — короткие имена + опциональный `course.json`

## Слои

```text
CLI / GUI
    ↓
course.convert_course / pipeline.convert_video
    ↓
encode.encode_file → ffmpeg_runner.run_ffmpeg
    ↓
probe / paths / temp_paths / windows_guard / session
```

GUI и CLI **делят одно ядро** — без копипасты ffmpeg argv.

## Ключевые решения продукта

| Решение | Выбор | Почему |
|---------|-------|--------|
| Метрика race | size@CQ + дисклеймер | Быстро, без VMAF; для курсов ок |
| UI | CLI first, затем CustomTkinter GUI | Скорость MVP |
| Encode | только NVENC | Скорость на RTX |
| Audio | copy по умолчанию | Не портить речь и не врать про экономию видео |
| Замена файлов | outbox, не in-place | Откат / прозрачность |

## Отмена и надёжность

1. Активные `Popen` регистрируются.
2. Stop / закрытие окна → `taskkill /F /T /PID`.
3. Encode пишет во временный `name.conv.<id>.ext`, затем atomic promote.
4. При старте/конце чистятся leftover `*.conv.*` под tmp.
5. При падении курса tmp курса сносится; outbox не остаётся полусобранным.

## Пропуск уже сжатого

`already_target_codec()` по `ffprobe codec_name`:

- auto → skip HEVC или AV1;
- force/locked → skip только совпадение с целевым кодеком.

## Сессионная статистика

`session.SessionStats` копит original/final по курсам → freed bytes, %, MiB/h для GUI и логов.

## Тестирование

Юнит-тесты мокают subprocess/ffmpeg. Порог coverage 90% без `gui.py`.

## Расширение

Хорошие точки роста без ломки ADR-0001:

- чтение `course.json` в GUI/отчётах;
- профили CQ в TOML;
- duplicate scan по title/publishers из JSON;
- опциональный VMAF hybrid позже.
