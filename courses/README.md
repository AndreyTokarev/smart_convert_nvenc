# Courses / Курсы

Default pipeline directories (see ADR-0001: [EN](../docs/en/adr/0001-course-inbox-outbox-tmp.md) · [RU](../docs/ru/adr/0001-course-inbox-outbox-tmp.md)).

Каталоги конвейера по умолчанию (см. ADR-0001).

| Folder / Папка | Role / Роль |
|----------------|-------------|
| [inbox/](./inbox/) | Source course folders / исходные папки курсов |
| [outbox/](./outbox/) | Result: compressed or original / результат: сжатый или исходный |
| [tmp/](./tmp/) | Encode work area / рабочая зона encode (не кладите сюда исходники вручную) |

Override with `--courses-root` / `--inbox` / `--outbox` / `--tmp` or `SMART_CONVERT_*` env vars.

Course media is not stored in git. / Медиа курсов в git не хранятся.
