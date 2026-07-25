# План оставшейся работы — smart_convert_nvenc

English: [../en/remaining-work-plan.md](../en/remaining-work-plan.md).

- **Статус:** R0–R1 сделаны; R2–R3 ожидают
- **Дата:** 2026-07-26 (правка после thermo-nuclear review; R1 реализован)
- **Контекст:** После F1–F6 и релиза **v0.1.8** обязательный feature-port и продуктовый roadmap закрыты. Здесь — **что ещё нет**: polish UX архива, опции честности/качества encode, ops/release hardening.

Связанные документы:

- [feature-port-plan.md](./feature-port-plan.md) — F1–F6 **done**
- [refactoring-plan.md](./refactoring-plan.md) — решения + фаза B
- [ARCHITECTURE.md](./ARCHITECTURE.md) — расширения ссылаются сюда

---

## Порядок работ

```text
R0 (гигиена планов) → R1.0 (разбиение GUI) → R1.1–R1.4 (UX) → R2 (encode) → R3 (ops/release)
```

Не помечать release zip как «поддерживаемые» (R3.3), пока на машине maintainer не прогнан GPU smoke (R3.2).  
Не начинать UI для R1.1–R1.3, пока не закрыт **R1.0** (или тот же PR доказывает, что `gui.py` не растёт по строкам).

---

## Ограничения дизайна (жёсткие гейты)

Блокеры на ревью для PR с R1+:

1. **Бюджет `gui.py`:** уже ~987 LOC. R1 не должен перевести файл за **1000** без предварительного разбиения. Сначала extract (R1.0). PR падает на ревью, если `gui.py` растёт и нет split-PR.
2. **Единая граница `course.json`:** `course_meta.py` — **единственный** парсер/нормализатор. GUI, `session.py` и `duplicates.py` не делают свой `json.loads` корня курса.
3. **Профиль = путь CLI:** GUI сидирует виджеты через `get_profile(name).to_convert_settings(...)`; значения виджетов — **overrides** (как флаги CLI поверх `--profile`). Не дублировать математику profile→settings в GUI.
4. **R2.1:** `N=1` и `N>1` — один код path sample/average, без второго pipeline за `if fragments > 1`.
5. **R3.1:** лог-файл — отдельный sink-модуль; в GUI остаётся только ring-buffer.

---

## R0 — Гигиена планов

Выровнять старые планы под уже сделанное (без нового поведения продукта).

| # | Задача | Статус |
|---|--------|--------|
| R0.1 | Отметить **сделанные** Phase 0–4 и *ядро* Phase 5; smoke/file-logs оставить открытыми → R3 | сделано |
| R0.2 | Заголовок решений `1C 2C 3C 4C 5` (было устаревшее `3A`) | сделано |
| R0.3 | Phase B «same volume» → `[x]` (уже в ADR-0001) | сделано |
| R0.4 | Правки backlog по thermo-nuclear (R1.0, контракт `course_meta`, seed профиля, честность Phase 5) | сделано |

---

## R1 — Polish UX архива

### R1.0 — Разбиение GUI (обязательный пререквизит)

`gui.py` — God-`App` (layout, список курсов, settings, job/worker, progress, логи). Разбить **до** UI для `course.json` и выбора профиля.

Предлагаемый extract (без смены поведения):

| Кусок | Куда |
|-------|------|
| Layout / path rows / панели `_build` | `gui_layout.py` или panel builders |
| Refresh списка / selection / labels | `gui_course_list.py` |
| Run / stop / очереди progress | `gui_job.py` |
| Только wiring + mainloop | `gui.py` (`App`) |

**Критерий готовности:** `gui.py` явно под 1k с запасом; list/job/layout снаружи; GUI settings/тесты зелёные.

### R1.1–R1.4 — Фичи (после R1.0)

| # | Задача | Куда |
|---|--------|------|
| R1.1 | Читать/показывать `course.json` (title, publishers, authors, year) в списке + tooltips | `course_meta.py` (load + `display_label`); **только course-list модуль** для Tk; [ADR-0002](./adr/0002-course-folder-naming.md) |
| R1.2 | Поля метаданных в `session-report.md` и отчёте дубликатов | `session.py` / `duplicates.py` **только через `load_course_meta`** |
| R1.3 | Выбор профиля в GUI (`default` / `course`) в `GuiSettings`; seed через `get_profile → to_convert_settings`; виджеты — overrides | `gui_settings.py`, `profiles.py`, тонкий wiring GUI |
| R1.4 | Более богатые дубликаты: нормализованный title / пересечение publishers (**только отчёт**) | `duplicates.py` + helpers в `course_meta` |

**Контракт `course_meta.py` (минимум):**

- Frozen `CourseMeta` по полям ADR-0002
- `load_course_meta(course_root) -> CourseMeta | None`
- `normalize_title` / publisher-overlap для R1.4
- `display_label(folder_name, meta) -> str` (**без** Tk)

**Критерий готовности:** GUI показывает title из JSON; выбор `course` совпадает с `uv run smart-convert-course --profile course`; отчёт дубликатов группирует по JSON title; **второго парсера `course.json` в `src/` нет**.

---

## R2 — Качество / честность encode (после R1)

| # | Задача | Заметки |
|---|--------|---------|
| R2.1 | Multi-fragment sample (N клипов → средний размер / VMAF) | `pipeline.py`; `--sample-fragments N` (default `1`); один path для любого N |
| R2.2 | Опциональный NVENC multipass / lookahead | поля settings/profile → один argv assembler в `encode.py`; **выкл. по умолчанию** |
| R2.3 | Задокументированное CQ↔CRF для CPU vs NVENC (или отдельные CRF defaults) | `profiles.toml` + USER_GUIDE; не намекать «одно число = одно качество» |

**Критерий готовности:** `--sample-fragments 3` в тестах с моками; CRF defaults для CPU в доках; multipass — opt-in.

---

## R3 — Ops / ужесточение релизов (последним)

| # | Задача | Заметки |
|---|--------|---------|
| R3.1 | Опциональный лог-файл (путь в settings / `%APPDATA%`) | отдельный sink-модуль; ring-buffer GUI без изменений; CLI/session могут подключить тот же sink |
| R3.2 | Опциональный GPU smoke (skip без NVENC) | `scripts/smoke_nvenc.py` и/или opt-in тест; в CI **не** обязателен |
| R3.3 | Планка поддержки release zip + smoke Win+NVIDIA; затем смягчить/убрать «unsupported» в [RELEASES.md](./RELEASES.md) | только после зафиксированного smoke |

**Критерий готовности:** путь лога в доках; smoke-скрипт есть; RELEASES меняется только после реального smoke.

---

## Явно вне скоупа

- Автоудаление / автоперенос дубликатов без подтверждения
- AMD / Intel QSV
- Облако / стриминг-профили
- Допиливание старого репозитория `video_converter`
- Параллельные NVENC-сессии

---

## Журнал выполнения

| Фаза | Статус | Дата | Комментарий |
|------|--------|------|-------------|
| R0 | сделано | 2026-07-26 | Гигиена + backlog; R0.4 правки review |
| R1.0 | сделано | 2026-07-26 | Разбиение GUI |
| R1.1–R1.4 | сделано | 2026-07-26 | `course_meta`, профиль в GUI, метаданные в отчётах |
| R2 | ожидает | — | |
| R3 | ожидает | — | |
