# Remaining work plan — smart_convert_nvenc

Русский: [../ru/remaining-work-plan.md](../ru/remaining-work-plan.md).

- **Status:** R0–R1 done; R2–R3 pending
- **Date:** 2026-07-26 (revised after thermo-nuclear review; R1 implemented)
- **Context:** After F1–F6 and release **v0.1.8**, the required feature-port and product roadmap are complete. This plan tracks what is **still missing**: archive UX polish, encode honesty/quality options, and ops/release hardening.

Related:

- [feature-port-plan.md](./feature-port-plan.md) — F1–F6 **done**
- [refactoring-plan.md](./refactoring-plan.md) — decisions + Phase B
- [ARCHITECTURE.md](./ARCHITECTURE.md) — points here for extensions

---

## Work order

```text
R0 (docs hygiene) → R1.0 (GUI split) → R1.1–R1.4 (UX) → R2 (encode) → R3 (ops/release)
```

Do not mark release zips “supported” (R3.3) until a maintainer GPU smoke (R3.2) has been run once.  
Do not start R1.1–R1.3 UI work until **R1.0** lands (or the same PR proves net `gui.py` line count does not rise).

---

## Design constraints (hard gates)

These are review blockers for R1+ PRs:

1. **`gui.py` budget:** already ~987 LOC. R1 must not push it past **1000** without a prior decompose. Prefer extract-first (R1.0). Fail review if `gui.py` grows and no split PR exists.
2. **Single `course.json` boundary:** `course_meta.py` is the **only** parser/normalizer. GUI, `session.py`, and `duplicates.py` must not `json.loads` course roots themselves.
3. **Profile = CLI path:** GUI uses `get_profile(name).to_convert_settings(...)` to seed widgets; widget values are **overrides** (same semantics as CLI flags over `--profile`). Do not reimplement profile→settings math in the GUI.
4. **R2.1:** `N=1` and `N>1` share one sample/average code path — no twin pipeline behind `if fragments > 1`.
5. **R3.1:** file log is a separate sink module; GUI keeps the ring-buffer only.

---

## R0 — Plan hygiene

Keep old plans aligned with shipped reality (no new product behavior).

| # | Task | Status |
|---|------|--------|
| R0.1 | Mark **shipped** Phase 0–4 and Phase 5 *core* done; leave smoke/file-logs open → R3 | done |
| R0.2 | Decision header `1C 2C 3C 4C 5` (was stale `3A`) | done |
| R0.3 | Phase B “same volume” recommendation `[x]` (already in ADR-0001) | done |
| R0.4 | Thermo-nuclear fixes to this backlog (R1.0, `course_meta` contract, profile seeding, Phase 5 honesty) | done |

---

## R1 — Archive UX polish

### R1.0 — GUI decompose (prerequisite)

`gui.py` is a God-`App` (layout, course list, settings, job/worker, progress, logs). Split **before** adding course JSON UI or profile picker.

Suggested extract (behavior-preserving):

| Piece | Suggested home |
|-------|----------------|
| Layout / path rows / `_build` panels | `gui_layout.py` or panel builders |
| Course list refresh / selection / labels | `gui_course_list.py` |
| Run / stop / progress queues | `gui_job.py` |
| Wiring + mainloop only | `gui.py` (`App`) |

**Done when:** `gui.py` is clearly under 1k with room for small wiring; list/job/layout live elsewhere; existing GUI tests/settings still green.

### R1.1–R1.4 — Features (after R1.0)

| # | Task | Target |
|---|------|--------|
| R1.1 | Load/display `course.json` (title, publishers, authors, year) in course list + tooltips | `course_meta.py` (load + `display_label`); **course-list module** only for Tk wiring; [ADR-0002](./adr/0002-course-folder-naming.md) |
| R1.2 | Metadata fields in `session-report.md` and duplicate report when JSON present | `session.py` / `duplicates.py` via **`load_course_meta` only** |
| R1.3 | GUI profile picker (`default` / `course`) on `GuiSettings`; seed via `get_profile → to_convert_settings`; widgets override | `gui_settings.py`, `profiles.py`, thin GUI wiring |
| R1.4 | Richer duplicates: normalized title / overlapping publishers from JSON (**report only**) | `duplicates.py` + helpers in `course_meta` (normalize/match) |

**`course_meta.py` contract (minimum):**

- Frozen `CourseMeta` matching ADR-0002 fields
- `load_course_meta(course_root) -> CourseMeta | None`
- `normalize_title` / publisher-overlap helpers for R1.4
- `display_label(folder_name, meta) -> str` (**no** Tk imports)

**Done when:** GUI shows title from JSON; choosing `course` matches `uv run smart-convert-course --profile course`; duplicate report can group by JSON title; **no second `course.json` parser** anywhere in `src/`.

---

## R2 — Encode quality / honesty (after R1)

| # | Task | Notes |
|---|------|--------|
| R2.1 | Multi-fragment sample (N clips → average size / VMAF) | `pipeline.py`; `--sample-fragments N` (default `1`); one path for all N |
| R2.2 | Optional NVENC multipass / lookahead | settings/profile fields → single argv assembler in `encode.py`; **off by default** |
| R2.3 | Documented CQ↔CRF mapping for CPU vs NVENC (or separate CRF defaults in profiles) | `profiles.toml` + USER_GUIDE; do not imply “same number = same quality” |

**Done when:** `--sample-fragments 3` works under mocked tests; CPU CRF defaults documented; multipass is opt-in.

---

## R3 — Ops / release hardening (last)

| # | Task | Notes |
|---|------|--------|
| R3.1 | Optional session/app log file (path in settings / `%APPDATA%`) | new sink module; GUI ring-buffer unchanged; CLI/session may attach the same sink |
| R3.2 | Optional GPU smoke (skip if no NVENC) | `scripts/smoke_nvenc.py` and/or opt-in test; **not** required in CI |
| R3.3 | Release zip support bar: checklist + smoke on Win+NVIDIA; then soften/remove “unsupported” in [RELEASES.md](./RELEASES.md) | only after recorded smoke evidence |

**Done when:** log path documented; smoke script exists; RELEASES wording updated only after a real smoke pass.

---

## Explicitly out of scope

- Auto-delete / auto-move duplicates without confirmation
- AMD / Intel QSV
- Cloud / streaming profiles
- Extending the old `video_converter` repository
- Parallel NVENC sessions

---

## Execution log

| Phase | Status | Date | Comment |
|-------|--------|------|---------|
| R0 | done | 2026-07-26 | Hygiene + backlog; R0.4 review fixes |
| R1.0 | done | 2026-07-26 | GUI split (`gui_layout` / `gui_course_list` / `gui_job` / …) |
| R1.1–R1.4 | done | 2026-07-26 | `course_meta`, profile picker, session/dupe metadata |
| R2 | pending | — | |
| R3 | pending | — | |
