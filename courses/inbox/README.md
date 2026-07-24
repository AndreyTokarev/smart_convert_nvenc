# inbox

**EN:** Put a full **course folder** here, for example:

**RU:** Положите сюда целую **папку курса**, например:

```text
courses/inbox/[0000] 20 Sick Licks/
  course.json          # optional metadata + course-root marker (ADR-0002)
  Lick 01/
    lesson.mp4
  slides.pdf
```

Optional `course.json` / опциональный `course.json`:

```json
{
  "schema": 1,
  "title": "20 Sick Licks",
  "year": null,
  "publishers": ["Jam Track Central"],
  "authors": ["Matteo Mancuso"],
  "notes": ""
}
```

After processing, the course leaves this folder and appears under `courses/outbox/` (including `course.json` if present).

После обработки курс уходит из этой папки в `courses/outbox/` (вместе с `course.json`, если был).

ADR-0002: [EN](../../docs/en/adr/0002-course-folder-naming.md) · [RU](../../docs/ru/adr/0002-course-folder-naming.md).
