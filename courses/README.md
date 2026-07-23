# Courses

Default pipeline directories (see [ADR-0001](../docs/adr/0001-course-inbox-outbox-tmp.md)).

| Folder | Role |
|--------|------|
| [inbox/](./inbox/) | Source course folders go here |
| [outbox/](./outbox/) | Result: compressed course, or original if compression was not worth it |
| [tmp/](./tmp/) | Encode work area; do not put source courses here manually |

Override with `--courses-root` / `--inbox` / `--outbox` / `--tmp` or `SMART_CONVERT_*` env vars.

Course media is not stored in git.
