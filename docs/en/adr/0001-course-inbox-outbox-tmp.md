# ADR-0001: Course pipeline `inbox → tmp → outbox`

Русский: [../../ru/adr/0001-course-inbox-outbox-tmp.md](../../ru/adr/0001-course-inbox-outbox-tmp.md).

- **Status:** Accepted
- **Date:** 2026-07-24
- **Context:** large video-course archive, limited disk space, real courses tested inside the repo

## Context

Needed flow:

1. Drop a course folder (all files) into **inbox**.
2. Tool compresses videos via NVENC.
3. If **total course size decreased** — move compressed tree to **outbox** **including all non-video files**.
4. If **not smaller** — move the **original** course to **outbox** as-is.
5. Inbox is emptied for that course after processing.

Disk is tight: do **not** fully duplicate a course into tmp for the whole run.

**Folder names are English-only** (ASCII) for tooling/git/terminals on Windows.

## Decision

### Paths: defaults inside the project, all overridable

**Default root:** `<repo_root>/courses/`  
(repo root = directory with `pyproject.toml` / this git repo — not necessarily the process cwd).

| Role | Default | Override |
|------|---------|----------|
| Inbox | `<project>/courses/inbox` | CLI `--inbox` / env `SMART_CONVERT_INBOX` |
| Outbox | `<project>/courses/outbox` | CLI `--outbox` / env `SMART_CONVERT_OUTBOX` |
| Work (`tmp`) | `<project>/courses/tmp` | CLI `--tmp` / env `SMART_CONVERT_TMP` |
| Root of the three | `<project>/courses` | CLI `--courses-root` (then `inbox`/`outbox`/`tmp` are children unless set explicitly) |

Priority: **CLI flag > env > project default**.

Why defaults in-repo: easy manual tests next to the code.  
Why override: production archive may live on another drive; keep the three dirs on **one volume** so `move` is not copy+delete.

### Default layout

```text
<project>/courses/
  inbox/    # source courses
  outbox/   # result (compressed or original)
  tmp/      # encode work only; not long-term storage
```

| Path (default) | Role |
|----------------|------|
| `…/inbox/<course_name>/` | Unit of work = **one first-level folder** |
| `…/outbox/<course_name>/` | Final location after processing |
| `…/tmp/<course_name>/` | Temporary encodes; cleaned after success/skip |

Media is **not** committed (gitignore contents of the default tree); only README stubs stay in git. Override paths outside the repo are the user's responsibility.

### Unit of work

- **Course** = directory `courses/inbox/<name>/` (recursive: videos, PDFs, code, subs, …).
- Loose files directly under `inbox/` (not in a course folder) are out of scope for v1 (error + hint).
- Ideal short folder name + optional `course.json` metadata/root marker: [ADR-0002](./0002-course-folder-naming.md). The pipeline treats the folder name as opaque identity and does not rename it.

### When a course “got smaller”

Compare **full tree size** (all files), not videos only:

`size(assembled) < size(original_course) * (1 - min_course_savings)`

Default threshold similar to per-file savings (e.g. 5–10%), via `--min-course-savings`.

Per video, MVP logic still applies (HEVC vs AV1 sample, skip file if not worth it). Course total = chosen videos + untouched non-video.

### Processing flow (space-conscious)

Do **not** copy the whole course into tmp.

1. `original_size = du(courses/inbox/Name)`.
2. For each video:
   - encode to `courses/tmp/Name/<relative_path_with_new_ext>`;
   - if compressed is **not** smaller (per-file threshold) — keep original, delete failed tmp output;
   - if smaller — mark compressed as winner.
3. Do **not** pre-copy non-video into tmp; count their size from `inbox/`.
4. `candidate_size` = sum(chosen videos) + all non-video sizes.
5. **If candidate is worth it:**
   - assemble `courses/outbox/Name/`:
     - non-video: `move` from `inbox` (same volume → rename);
     - winning videos: `move` from `tmp`;
     - losing videos: `move` originals from `inbox`;
   - remove emptied `inbox/Name` and `tmp/Name`.
6. **If not worth it:**
   - `move courses/inbox/Name → courses/outbox/Name`;
   - delete `tmp/Name` entirely.
7. On mid-flight error: leave course in `inbox/` (or mark `Name.failed`); optionally keep tmp for debug; **never publish a partial tree to `outbox/`**.

### Name conflicts

If `courses/outbox/Name` already exists — **fail** (no silent overwrite). Later: `--overwrite-outbox` or date suffix.

### Why `tmp` is required

Without a separate work dir you cannot:

- keep the source intact until the course-level decision;
- compare sizes without corrupting inbox;
- discard a bad compression simply by deleting tmp.

`tmp/` is disposable; after a successful course run it should not retain that course.

### CLI (next implementation step)

```text
uv run smart-convert-course
uv run smart-convert-course "Name"

uv run smart-convert-course --courses-root "D:\Archive\courses"
uv run smart-convert-course --inbox "E:\inbox" --outbox "E:\outbox" --tmp "E:\work"
```

Single-file `smart-convert path.mp4` stays for codec debugging; archive UX is the folder pipeline.

## Consequences

### Pros

- Clear inbox/outbox naming for manual tests inside the project.
- Production paths can live on another disk without code changes.
- English ASCII folder names avoid Windows console/git path pain.
- Non-video files preserved on success.
- Unprofitable courses move as originals; tmp is discarded.
- No mandatory full course duplicate.

### Cons / risks

- Encode needs free space ≈ size of videos being compressed while tmp exists.
- Cross-volume `move` becomes copy+delete — keep inbox/outbox/tmp on one volume.
- Mixed courses (some videos shrink, some do not) need careful assembly — supported by design.
- Must resolve project root reliably when installed editable from another cwd.

## Alternatives rejected

| Alternative | Why not |
|-------------|---------|
| In-place encode in `inbox/` | Cannot roll back cleanly; corrupts inbox |
| Always copy to `outbox/`, then encode | Doubles disk use |
| Only `tmp/` without `outbox/` | No stable outbox |
| `before`/`after` folder names | User prefers `inbox`/`outbox` |
| Cyrillic default folder names | User requires English-only paths |
| Paths fixed inside the project only | Cannot point at archive on another drive |
| Env only, no CLI | Awkward for one-off runs |
| “Course smaller” by video size only | Ignores materials; user thinks in whole courses |

## Related

- Decision log: 1B / 2C / 3A / 4C in [refactoring-plan.md](../refactoring-plan.md)
- Pipeline implementation — next after single-file MVP
