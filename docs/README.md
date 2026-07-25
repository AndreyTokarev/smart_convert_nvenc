# Документация / Documentation — smart_convert_nvenc

Лицензия / License: **MIT** ([LICENSE](../LICENSE)).

Версия / Version: see [CHANGELOG.md](../CHANGELOG.md) · [CHANGELOG.ru.md](../CHANGELOG.ru.md).

Все пользовательские и проектные документы ведутся **на двух языках**: `docs/en/` и `docs/ru/`.

All user-facing and design docs are maintained **in both languages**: `docs/en/` and `docs/ru/`.

## Guides

| | English | Русский |
|--|---------|---------|
| User guide | [en/USER_GUIDE.md](./en/USER_GUIDE.md) | [ru/USER_GUIDE.md](./ru/USER_GUIDE.md) |
| Architecture | [en/ARCHITECTURE.md](./en/ARCHITECTURE.md) | [ru/ARCHITECTURE.md](./ru/ARCHITECTURE.md) |
| Releases (Win/Linux/macOS) | [en/RELEASES.md](./en/RELEASES.md) | [ru/RELEASES.md](./ru/RELEASES.md) |
| Local build (PyInstaller) | [en/BUILD.md](./en/BUILD.md) | [ru/BUILD.md](./ru/BUILD.md) |

## Design & history

| | English | Русский |
|--|---------|---------|
| Refactoring / decision journal | [en/refactoring-plan.md](./en/refactoring-plan.md) | [ru/refactoring-plan.md](./ru/refactoring-plan.md) |
| Feature port plan (F1–F6) | [en/feature-port-plan.md](./en/feature-port-plan.md) | [ru/feature-port-plan.md](./ru/feature-port-plan.md) |
| Codec chat review | [en/review-codec-advice.md](./en/review-codec-advice.md) | [ru/review-codec-advice.md](./ru/review-codec-advice.md) |
| Source chat archive | [en/chat-optimal-mpeg4-codec.md](./en/chat-optimal-mpeg4-codec.md) | [ru/chat-optimal-mpeg4-codec.md](./ru/chat-optimal-mpeg4-codec.md) |
| ADR index | [en/adr/README.md](./en/adr/README.md) | [ru/adr/README.md](./ru/adr/README.md) |
| ADR-0001 inbox/tmp/outbox | [en/adr/0001-course-inbox-outbox-tmp.md](./en/adr/0001-course-inbox-outbox-tmp.md) | [ru/adr/0001-course-inbox-outbox-tmp.md](./ru/adr/0001-course-inbox-outbox-tmp.md) |
| ADR-0002 course.json | [en/adr/0002-course-folder-naming.md](./en/adr/0002-course-folder-naming.md) | [ru/adr/0002-course-folder-naming.md](./ru/adr/0002-course-folder-naming.md) |

## Community / announcement

VK / forum draft posts are kept locally (`docs/community/`, gitignored) and are not part of the published repository.

Черновики постов для VK/форумов хранятся локально (`docs/community/`, в gitignore) и не входят в публичный репозиторий.

## Project purpose / Зачем проект

**EN:** Free disk space from large **video course** libraries by encoding lessons with NVENC (or CPU), deciding at **course** granularity, and publishing through a safe outbox flow. Sample races use size@CQ by default; when FFmpeg has `libvmaf`, hybrid VMAF can prefer quality-qualified winners.

**RU:** Освободить диск от большого архива **видеокурсов**: encode уроков через NVENC (или CPU), решение на уровне **курса**, публикация через безопасный outbox. Race по сэмплу — size@CQ; при наличии `libvmaf` гибридный VMAF может выбирать победителя с учётом порога качества.
