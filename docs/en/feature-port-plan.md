# Plan: port proven features from video_converter

Русский: [../ru/feature-port-plan.md](../ru/feature-port-plan.md).

- **Status:** F1–F5 done; F6 partial (F6.4 done)  
- **Date:** 2026-07-24  
- **Context:** `D:\projects\python\video_converter` — previous personal service (Flet + NVENC). Decided not to extend it, but build **smart_convert_nvenc** from scratch for the course archive. Below: what to port from old experience, in what order, and what we deliberately do not carry over.

## Why this plan exists

The old project already hardened “operational” pieces (FFmpeg cancel, temp, reports, tests, pack).  
The new one has the right product model: **course**, `inbox → tmp → outbox`, HEVC/AV1 race, savings threshold, CustomTkinter GUI.

Goal: port maturity of the old code **without** going back to in-place file replacement or changing the UI stack.

Related docs from the old project (reference only, do not copy blindly):

- `D:\projects\python\video_converter\docs\DISK_SPACE_OPTIMIZATION.md`
- `D:\projects\python\video_converter\docs\PROFILES.md`
- `D:\projects\python\video_converter\docs\BUILD.md`
- `D:\projects\python\video_converter\ROADMAP.md`

---

## Already in smart_convert_nvenc (do not rework)

| Feature | Where |
|---------|-------|
| Course pipeline inbox/tmp/outbox | ADR-0001, `course.py` |
| Sample race HEVC vs AV1 + min-savings | `pipeline.py` |
| File / course CLI | `cli.py`, `course_cli.py` |
| GUI + app/ffmpeg logs + progress bars | `gui.py` |
| Windows guard (sleep / `shutdown /a`) | `windows_guard.py` |
| English paths `courses/*` | `paths.py` |

---

## What we do NOT port

| Idea from video_converter | Why not |
|---------------------------|---------|
| In-place replace of source | Breaks inbox/outbox contract |
| Single profile without race as only policy | Smarter codec choice already exists |
| Flet UI / flet pack as main GUI | Already CustomTkinter |
| Slow-dirs at folder level as-is | Harmful for courses with 1–2 heavy lessons |
| “Processed” archive next to library | Role covered by `outbox/` |
| Parallel NVENC sessions | GPU already busy with one encode |

---

## Implementation phases

### Phase F1 — Process reliability (P0)

**Why:** Stop in GUI must actually kill FFmpeg; crash must not leave junk and block disk.

| # | Task | Reference in old code | Target in smart |
|---|------|----------------------|-----------------|
| F1.1 | Registry of active `Popen` + cancel | `core/ffmpeg.py` | `ffmpeg_runner.py` |
| F1.2 | Kill process tree on Windows (`taskkill /T /F`) | same | `ffmpeg_runner.py` / new `process_kill.py` |
| F1.3 | GUI Stop → cancel current encode, not only “after file” | GUI cancel | `gui.py` + runner |
| F1.4 | Unique temp encode names (`*.conv.<id>.*`) | `core/output_paths.py` | `course.py` / `encode.py` |
| F1.5 | Cleanup course tmp on crash / window close | finalize + interrupted cleanup | `course.py`, `gui.py` |
| F1.6 | Retry encode without `-hwaccel` if first run failed | `convert_video` retry | `pipeline.py` / `encode.py` |
| F1.7 | Explicit ffmpeg/ffprobe + `hevc_nvenc`/`av1_nvenc` check on GUI/CLI start | `validate_environment` | `probe.py` + GUI banner |

**Done when:** Stop aborts current ffmpeg within ≤2–3 s; after kill/crash `courses/tmp/<course>` is either clean or safely cleaned on next run.

### Phase F2 — Reporting and queue (P1)

**Why:** see how much space was actually reclaimed per session, and get first gigabytes faster.

| # | Task | Reference | Target |
|---|------|------------|--------|
| F2.1 | Session report: Σ bytes saved, time, **MiB/hour** | DISK_SPACE + formatters | new `session.py`, GUI + CLI |
| F2.2 | Per-course summary in App log (before/after/Δ) | models size_before/after | `course.py` |
| F2.3 | Sort videos inside course by size ↓ | idea A.1 | `course.py` `iter_videos` |
| F2.4 | Show FFmpeg `speed=` in live line | parse stats | `progress.py`, `gui.py` |
| F2.5 | Optional: sort courses in queue by total size ↓ | — | `gui.py` / `course_cli.py` |

**Done when:** after running 1–N courses, log/GUI shows “freed X MiB in T min (Y MiB/h)”.

### Phase F3 — GUI UX and resilience (P1/P2)

| # | Task | Reference | Target |
|---|------|------------|--------|
| F3.1 | Persist GUI settings (CQ, preset, codec, sample) between runs | `core/config.py` | `%APPDATA%/smart_convert_nvenc/settings.json` or next to project |
| F3.2 | Ring-buffer logs (line limit) so GUI does not balloon | `log_panel.py` | `gui.py` |
| F3.3 | Throttle progress bar updates (not more often than N ms) | view progress | `gui.py` |
| F3.4 | Confirm + cleanup on window close during job | partially done | finish together with F1 |
| F3.5 | “Open inbox / outbox” button in Explorer | folder picker idea | `gui.py` |

**Done when:** GUI restart restores previous CQ/preset; long run does not slow UI due to log.

### Phase F4 — Tests without GPU (P2)

| # | Task | Reference | Target |
|---|------|------------|--------|
| F4.1 | Tests for ffmpeg argv assembly / profile suffixes | test_core | `tests/` |
| F4.2 | Tests for `paths` / resolve override CLI+env | — | `tests/test_paths.py` |
| F4.3 | Tests for course assemble (mock sizes, no encode) | test_output_paths / archive | `tests/test_course_assemble.py` |
| F4.4 | Tests for parse `time=` / progress fraction | — | `tests/test_progress.py` |
| F4.5 | Tests for AudioSettings / ConvertSettings parse | — | `tests/test_models.py` |

**Done when:** `uv run pytest` (or unittest) green on machine without GPU requirement.

### Phase F5 — Packaging and profiles (P2/P3)

| # | Task | Reference | Target |
|---|------|------------|--------|
| F5.1 | Move CQ/preset/defaults to `profiles.toml` or JSON (no presers typos) | PROFILES.md | `src/.../data/profiles.toml` — **done** |
| F5.2 | “Course” profile (more aggressive CQ, opt. audio opus) | — | profiles + CLI `--profile` — **done** |
| F5.3 | Standalone exe build script + doc | BUILD.md / PyInstaller or similar | `scripts/build.ps1`, `docs/*/BUILD.md` — **done** |
| F5.4 | Vendor/PATH strategy for FFmpeg — **done** (bundle BtbN in Win/Linux zip + `SMART_CONVERT_FFMPEG_DIR` / PATH fallback) |

**Done when:** one profile runs via flag; (optional) exe build script/instructions exist.

### Phase F6 — Product next steps (already on roadmap, not from video_converter)

| # | Task |
|---|------|
| F6.1 | Find duplicate courses/files (report, no auto-delete) |
| F6.2 | Batch report for course batch to file (`session-report.md`) |
| F6.3 | VMAF/hybrid (decision 1B → later C) |
| F6.4 | CPU fallback x265/SVT-AV1 — **done** (`encoder`: gpu/cpu/auto; no CQ↔CRF recalibration) |

---

## Work order (recommended)

```text
F1 (cancel/temp/retry)  →  F2 (MiB/hour + sorting)  →  F3 (settings/logs)
        ↓
      F4 (tests)
        ↓
      F5 (profiles / build) as needed
        ↓
      F6 (duplicates etc.)
```

Do not start F5 pack until Stop and temp are stable (F1).

---

## Code port principles

1. **Rewrite for current architecture**, do not copy-paste modules 1:1 from `video_converter`.
2. Any port that touches “where the file goes” must align with [ADR-0001](./adr/0001-course-inbox-outbox-tmp.md).
3. Old repository — **reference only**, not a dependency or submodule.
4. After each phase — short manual checklist: 1 small course in inbox → outbox + Stop mid-encode.

---

## Execution log

| Phase | Status | Date | Comment |
|-------|--------|------|---------|
| F1 | done | 2026-07-24 | Popen registry + taskkill /T; hard GUI Stop; `*.conv.<id>.*` temps + cleanup; hwaccel retry; `validate_environment` on GUI/CLI start |
| F2 | done | 2026-07-24 | Session freed MiB/%/MiB/h; course totals; videos+courses sorted by size ↓; `speed=` in GUI progress |
| F3 | done | 2026-07-24 | Settings persist; Open inbox/outbox; confirm on close; log ring-buffer; progress drain keeps latest only |
| F4 | done | 2026-07-24 | `pytest` + `pytest-cov`, fail_under=90; GUI/`__main__` omitted from coverage metric; mocks, no GPU required |
| F5 | done | 2026-07-26 | F5.1–F5.3 profiles.toml + `--profile` + build.ps1/BUILD.md; F5.4 FFmpeg vendor |
| F6 | partial | 2026-07-25 | F6.4 CPU encode force + auto-fallback landed |

---

## Link to overall plan

Updates the roadmap in [refactoring-plan.md](./refactoring-plan.md): pipeline and GUI are done; F1–F5 done; next focus — F6 duplicates / session report / VMAF as needed.
