# ADR-0002: Course identity — short folder names + optional `course.json`

Русский: [../../ru/adr/0002-course-folder-naming.md](../../ru/adr/0002-course-folder-naming.md).

- **Status:** Accepted
- **Date:** 2026-07-24
- **Context:** personal video-course archive; Windows path length is already tight on deep trees; metadata must not make paths worse

## Context

Folder names like `[0000] Title [Publisher] [Author]` (or tagged `[pub:…]` / `[by:…]`) push against **MAX_PATH** on nested lesson folders. Metadata still matters for later batch tools (filter, duplicates, reports).

Need:

1. **Short** human folder names when possible.
2. **Rich** course-level metadata without stuffing it into the path.
3. A **marker** of “this directory is a course root” for future batch scans (not only “direct child of inbox”).

## Decision

### Split: path vs metadata

| Concern | Where it lives |
|---------|----------------|
| Filesystem identity / move target | Folder name (opaque; tool does not rename) |
| Year, title, publishers, authors, notes | Optional **`course.json`** in the **course root** |
| “Is this a course root?” | Presence of `course.json` (primary marker); under `inbox/` any first-level folder is still a course even without JSON (ADR-0001) |

### Folder name (target, optional polish)

Keep names **short**. Year placeholder is enough for casual sort; do **not** encode publisher/author in the path.

```text
[0000] 20 Sick Licks
[2024] Complete Jazz Guitar
20 Sick Licks
```

Untagged `[Publisher]` / `[Author]` in the folder name remain **allowed but discouraged** (path length).  
**Rejected for target:** tagged brackets `[pub:…]` `[by:…]` — extra characters with no upside once JSON exists.

### `course.json` (preferred metadata)

**Path:** `<course_root>/course.json`  
**Role:** course-root marker + metadata for the whole tree (all nested files/dirs inherit this course context).

Minimal schema (`schema` version field for forward compatibility):

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

| Field | Type | Notes |
|-------|------|--------|
| `schema` | int | Currently `1` |
| `title` | string | Canonical title (may differ from folder name) |
| `year` | int \| null | `null` or omit = unknown (same meaning as folder `[0000]`) |
| `publishers` | string[] | Empty / omit if unknown; several orgs → several entries |
| `authors` | string[] | Empty / omit if unknown |
| `notes` | string | Optional free text |

Rules:

- File is **optional**. Missing JSON → course still valid; metadata unknown.
- Tool **must preserve** `course.json` like any other non-video (move with the course to outbox).
- Tool **does not require** JSON to encode (MVP compressor unchanged).
- Future batch jobs: if a directory contains `course.json`, treat it as course root even outside the default inbox layout.
- Do **not** invent per-file sidecar JSON in MVP; course-level is enough.

### Runtime (MVP encode pipeline)

Unchanged from ADR-0001:

- Unit of work = first-level folder under `inbox/` (with or without `course.json`).
- Pass folder name through; do not auto-rename.
- No-video courses: pass-through to outbox (JSON goes with them).

### Future (not MVP)

- Read `course.json` in GUI / reports / duplicate detection (F6).
- Optional “write stub `course.json`” helper when ingesting a bare folder.
- Optional validate/`schema` bump when fields grow (e.g. tags, source URL).

## Consequences

- Paths stay shorter; metadata richness moves into one small file at the root.
- Batch tooling gets a reliable root marker without parsing folder-name folklore.
- Folder `[0000]` and JSON `"year": null` can coexist; when both exist, **JSON wins** for metadata display; folder name remains filesystem identity.
- Duplicate detection should prefer JSON title/publishers/authors over fragile name parsing.

## Rejected

| Alternative | Why not |
|-------------|---------|
| Tagged brackets in folder names (`pub:` / `by:`) | Lengthens paths; JSON is clearer |
| Require `course.json` before encode | Blocks compressing the existing archive |
| Auto-rename folders from JSON | Identity churn; outbox/duplicates risk |
| Hidden `.course.json` | Easy to miss in Explorer; visibility > cleverness |
| Per-file metadata JSON next to every video | Noise; course-level inheritance is enough for now |
