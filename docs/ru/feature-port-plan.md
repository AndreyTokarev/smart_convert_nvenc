# План: перенос проверенных фич из video_converter

English: [../en/feature-port-plan.md](../en/feature-port-plan.md).

- **Статус:** F1–F6 done (F6.3 hybrid VMAF)  
- **Дата:** 2026-07-24  
- **Контекст:** `D:\projects\python\video_converter` — предыдущий личный сервис (Flet + NVENC). Решено не допиливать его, а собрать **smart_convert_nvenc** с нуля под архив курсов. Ниже — что из старого опыта переносим сюда, в каком порядке, и чего сознательно не тащим.

## Зачем этот план

В старом проекте уже отлажены «операционные» вещи (отмена FFmpeg, temp, отчёты, тесты, pack).  
В новом — правильная продуктовая модель: **курс**, `inbox → tmp → outbox`, race HEVC/AV1, порог экономии, GUI на CustomTkinter.

Цель: перенести зрелость старого кода **без** возврата к in-place замене файлов и без смены UI-стека.

Связанные доки старого проекта (справочно, не копировать слепо):

- `D:\projects\python\video_converter\docs\DISK_SPACE_OPTIMIZATION.md`
- `D:\projects\python\video_converter\docs\PROFILES.md`
- `D:\projects\python\video_converter\docs\BUILD.md`
- `D:\projects\python\video_converter\ROADMAP.md`

---

## Уже есть в smart_convert_nvenc (не переделывать)

| Фича | Где |
|------|-----|
| Конвейер курса inbox/tmp/outbox | ADR-0001, `course.py` |
| Sample race HEVC vs AV1 + min-savings | `pipeline.py` |
| CLI файла / курса | `cli.py`, `course_cli.py` |
| GUI + app/ffmpeg логи + progress bars | `gui.py` |
| Windows guard (сон / `shutdown /a`) | `windows_guard.py` |
| English paths `courses/*` | `paths.py` |

---

## Что НЕ переносим

| Идея из video_converter | Почему нет |
|-------------------------|------------|
| In-place replace исходника | Ломает контракт inbox/outbox |
| Один профиль без race как единственная политика | Уже есть более умный выбор кодека |
| Flet UI / flet pack как основной GUI | Уже CustomTkinter |
| Slow-dirs на уровне папки «как есть» | Для курсов с 1–2 тяжёлыми уроками вредно |
| Архив «обработанных» рядом с библиотекой | Роль закрывает `outbox/` |
| Параллельные NVENC-сессии | GPU и так занят одним encode |

---

## Фазы внедрения

### Фаза F1 — Надёжность процессов (P0)

**Зачем:** Stop в GUI должен реально убивать FFmpeg; краш не должен оставлять мусор и блокировать диск.

| # | Задача | Ориентир в старом коде | Куда в smart |
|---|--------|------------------------|--------------|
| F1.1 | Реестр активных `Popen` + cancel | `core/ffmpeg.py` | `ffmpeg_runner.py` |
| F1.2 | Kill process tree на Windows (`taskkill /T /F`) | там же | `ffmpeg_runner.py` / новый `process_kill.py` |
| F1.3 | Stop в GUI → cancel текущего encode, не только «после файла» | GUI cancel | `gui.py` + runner |
| F1.4 | Уникальные temp-имена encode (`*.conv.<id>.*`) | `core/output_paths.py` | `course.py` / `encode.py` |
| F1.5 | Cleanup tmp курса при краше / закрытии окна | finalize + interrupted cleanup | `course.py`, `gui.py` |
| F1.6 | Retry encode без `-hwaccel`, если первый прогон упал | `convert_video` retry | `pipeline.py` / `encode.py` |
| F1.7 | Явная проверка ffmpeg/ffprobe + `hevc_nvenc` при старте GUI/CLI (`av1_nvenc` опционален; AV1 может идти через libsvtav1) | `validate_environment` | `probe.py` + GUI banner |

**Критерий готовности:** Stop обрывает текущий ffmpeg за ≤2–3 с; после kill/crash `courses/tmp/<course>` либо чист, либо безопасно чистится при следующем запуске.

### Фаза F2 — Отчётность и очередь (P1)

**Зачем:** видеть, сколько места реально отвоевали за сессию, и быстрее получать первые гигабайты.

| # | Задача | Ориентир | Куда |
|---|--------|----------|------|
| F2.1 | Session report: Σ сэкономленных байт, время, **МБ/час** | DISK_SPACE + formatters | новый `session.py`, GUI + CLI |
| F2.2 | Итог по каждому курсу в App log (до/после/Δ) | models size_before/after | `course.py` |
| F2.3 | Сортировка видео внутри курса по размеру ↓ | идея A.1 | `course.py` `iter_videos` |
| F2.4 | Показывать `speed=` из FFmpeg в live-строке | parse stats | `progress.py`, `gui.py` |
| F2.5 | Опционально: сортировка курсов в очереди по суммарному размеру ↓ | — | `gui.py` / `course_cli.py` |

**Критерий готовности:** после прогона 1–N курсов в логе/GUI есть «freed X MiB in T min (Y MiB/h)».

### Фаза F3 — UX и устойчивость GUI (P1/P2)

| # | Задача | Ориентир | Куда |
|---|--------|----------|------|
| F3.1 | Сохранение настроек GUI (CQ, preset, codec, sample) между запусками | `core/config.py` | `%APPDATA%/smart_convert_nvenc/settings.json` или рядом с проектом |
| F3.2 | Ring-buffer логов (лимит строк), чтобы GUI не раздувался | `log_panel.py` | `gui.py` |
| F3.3 | Throttle обновлений progress bar (не чаще N мс) | view progress | `gui.py` |
| F3.4 | Confirm + cleanup при закрытии окна во время job | уже частично | добить вместе с F1 |
| F3.5 | Кнопка «Open inbox / outbox» в проводнике | folder picker идея | `gui.py` |

**Критерий готовности:** перезапуск GUI поднимает прошлые CQ/preset; длинный прогон не тормозит UI из‑за лога.

### Фаза F4 — Тесты без GPU (P2)

| # | Задача | Ориентир | Куда |
|---|--------|----------|------|
| F4.1 | Тесты сборки ffmpeg argv / суффиксов профиля | test_core | `tests/` |
| F4.2 | Тесты `paths` / resolve override CLI+env | — | `tests/test_paths.py` |
| F4.3 | Тесты course assemble (mock sizes, без encode) | test_output_paths / archive | `tests/test_course_assemble.py` |
| F4.4 | Тесты parse `time=` / progress fraction | — | `tests/test_progress.py` |
| F4.5 | Тесты AudioSettings / ConvertSettings parse | — | `tests/test_models.py` |

**Критерий готовности:** `uv run pytest` (или unittest) зелёный на машине без требования GPU.

### Фаза F5 — Упаковка и профили (P2/P3)

| # | Задача | Ориентир | Куда |
|---|--------|----------|------|
| F5.1 | Вынести CQ/preset/defaults в `profiles.toml` или JSON (без опечаток presers) | PROFILES.md | `src/.../data/profiles.toml` — **сделано** |
| F5.2 | Профиль «course» (агрессивнее CQ, опц. audio opus) | — | profiles + CLI `--profile` — **сделано** |
| F5.3 | Скрипт сборки standalone exe + doc | BUILD.md / PyInstaller или аналог | `scripts/build.ps1`, `docs/*/BUILD.md` — **сделано** |
| F5.4 | Vendor/PATH strategy для FFmpeg — **сделано** (BtbN в Win/Linux zip + `SMART_CONVERT_FFMPEG_DIR` / PATH fallback) |

**Критерий готовности:** один профиль запускается флагом; (опционально) есть инструкция/скрипт сборки exe.

### Фаза F6 — Дальше по продукту (уже в roadmap, не из video_converter)

| # | Задача |
|---|--------|
| F6.1 | Поиск дубликатов курсов/файлов (отчёт, без автоудаления) — **сделано** (`duplicates` / `smart-convert-duplicates`) |
| F6.2 | Batch-отчёт по пачке курсов в файл (`session-report.md`) — **сделано** |
| F6.3 | VMAF/гибрид (решение 1B → позже C) — **сделано** (`vmaf=auto|off|on`, порог `vmaf_min`) |
| F6.4 | CPU fallback x265/SVT-AV1 — **сделано** (`encoder`: gpu/cpu/auto; без перекалибровки CQ↔CRF) |

---

## Порядок работ (рекомендуемый)

```text
F1 (cancel/temp/retry)  →  F2 (МБ/час + сортировка)  →  F3 (settings/logs)
        ↓
      F4 (tests)
        ↓
      F5 (profiles / build) по необходимости
        ↓
      F6 (дубликаты и т.д.)
```

Не начинать F5 pack, пока Stop и temp не стабильны (F1).

---

## Принципы переноса кода

1. **Переписывать под текущую архитектуру**, не копипастить модули 1:1 из `video_converter`.
2. Любой перенос, который трогает «куда девается файл», сверять с [ADR-0001](./adr/0001-course-inbox-outbox-tmp.md).
3. Старый репозиторий — **справочник**, не зависимость и не submodule.
4. После каждой фазы — короткий чеклист вручную: 1 маленький курс в inbox → outbox + Stop mid-encode.

---

## Журнал выполнения

| Фаза | Статус | Дата | Комментарий |
|------|--------|------|-------------|
| F1 | done | 2026-07-24 | Popen registry + taskkill /T; hard GUI Stop; `*.conv.<id>.*` temps + cleanup; hwaccel retry; `validate_environment` on GUI/CLI start |
| F2 | done | 2026-07-24 | Session freed MiB/%/MiB/h; итоги курса; видео+курсы по размеру ↓; `speed=` в прогрессе GUI |
| F3 | done | 2026-07-24 | Persist настроек; Open inbox/outbox; confirm при закрытии; ring-buffer логов; progress drain — только latest |
| F4 | done | 2026-07-24 | `pytest` + `pytest-cov`, fail_under=90; GUI/`__main__` omitted from coverage metric; mocks, no GPU required |
| F5 | done | 2026-07-26 | F5.1–F5.3 profiles.toml + `--profile` + build.ps1/BUILD.md; F5.4 FFmpeg vendor |
| F6 | done | 2026-07-26 | F6.1 дубликаты; F6.2 session-report; F6.3 hybrid VMAF; F6.4 CPU encode |

---

## Связь с общим планом

Обновляет дорожную карту в [refactoring-plan.md](./refactoring-plan.md): конвейер и GUI уже сделаны; F1–F6 done. Дальше: [remaining-work-plan.md](./remaining-work-plan.md).
