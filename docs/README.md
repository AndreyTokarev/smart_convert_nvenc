# Документация / Documentation — smart_convert_nvenc

Лицензия: **MIT** ([LICENSE](../LICENSE)).

## User-facing guides

| | English | Русский |
|--|---------|---------|
| User guide | [en/USER_GUIDE.md](./en/USER_GUIDE.md) | [ru/USER_GUIDE.md](./ru/USER_GUIDE.md) |
| Architecture | [en/ARCHITECTURE.md](./en/ARCHITECTURE.md) | [ru/ARCHITECTURE.md](./ru/ARCHITECTURE.md) |
| Releases (Win/Linux/macOS) | [en/RELEASES.md](./en/RELEASES.md) | [ru/RELEASES.md](./ru/RELEASES.md) |

## Community / announcement

VK / forum draft posts are kept locally (`docs/community/`, gitignored) and are not part of the published repository.

## Design & history

| Document | Description |
|----------|-------------|
| [refactoring-plan.md](./refactoring-plan.md) | Goal, decision journal (1B/2C/3A/4C), roadmap |
| [feature-port-plan.md](./feature-port-plan.md) | Port plan from earlier video_converter (F1–F6) |
| [adr/README.md](./adr/README.md) | Architecture Decision Records |
| [adr/0001-course-inbox-outbox-tmp.md](./adr/0001-course-inbox-outbox-tmp.md) | Course pipeline `inbox → tmp → outbox` |
| [adr/0002-course-folder-naming.md](./adr/0002-course-folder-naming.md) | Short folder names + optional `course.json` |
| [review-codec-advice.md](./review-codec-advice.md) | Review of earlier codec chat |
| [chat-optimal-mpeg4-codec.md](./chat-optimal-mpeg4-codec.md) | Source chat archive |

## Project purpose (one paragraph)

Free disk space from large **video course** libraries by GPU-encoding lessons with NVENC, deciding at **course** granularity, and publishing results through a safe outbox flow — without pretending sample size races are VMAF-equal quality.
