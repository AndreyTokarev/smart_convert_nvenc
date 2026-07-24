# inbox

Put a full **course folder** here, for example:

```text
courses/inbox/[0000] 20 Sick Licks/
  course.json          # optional metadata + course-root marker (ADR-0002)
  Lick 01/
    lesson.mp4
  slides.pdf
```

Optional `course.json` example:

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
