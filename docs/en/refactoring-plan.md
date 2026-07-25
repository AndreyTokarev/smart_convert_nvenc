# Refactoring plan: smart_convert_nvenc

Русский: [../ru/refactoring-plan.md](../ru/refactoring-plan.md).

Status: decisions accepted (1C 2C 3C 4C 5) — F1–F6 done; remaining work → [remaining-work-plan.md](./remaining-work-plan.md)
Basis: [review-codec-advice.md](./review-codec-advice.md), source chat [chat-optimal-mpeg4-codec.md](./chat-optimal-mpeg4-codec.md)

## Product goal (why this exists)

The archive owner stores **a very large number of video courses** (lessons, screen recordings, slides + speech). They take up an unreasonable amount of space; some files may be **duplicates**. The goal is to **free disk space** so new courses can be downloaded.

Practical purpose of the tool:
1. Find and (optionally) remove/mark **duplicates**.
2. **Compress** remaining videos so slides/text remain readable and speech is intelligible — cinematic quality is not required.
3. Do this **in folder batches** and **quickly** (RTX 4060 Ti / NVENC), without manual HandBrake on every file.
4. Do not spend time on files that are already well compressed (savings threshold).

Success criterion: gigabytes/terabytes of free space at acceptable quality for learning, not “perfect VMAF”.

Technical sub-goal: on a sample, choose between **HEVC NVENC** and **AV1 NVENC** (or lock in one profile), then full encode if it makes sense.

---

## Principles

1. **Primary metric — space saved**, at “good enough” quality for courses (readable slides, speech).
2. On the sample test, **do not mix audio codecs** (`-c:a copy`), so video gains are not misreported.
3. **Full encode only if better than the source** (savings threshold).
4. **Batch folder processing** — part of the product, not “someday later”.
5. **Course pipeline:** default `courses/inbox` → `courses/tmp` → `courses/outbox` inside the project; paths are **overridable**; folder names **English only**. See [ADR-0001](./adr/0001-course-inbox-outbox-tmp.md). Course metadata — optional [`course.json`](./adr/0002-course-folder-naming.md) at the root (do not bloat the path).
6. **CLI and GUI share one core** (no copy-pasted FFmpeg commands).
7. Stack: **Python + uv**, FFmpeg with NVENC required.
8. Do not duplicate the entire course on disk unnecessarily (limited space — `tmp` only for encode).

---

## Phases

> Checkboxes below reflect the **shipped** MVP/core. Open follow-ups (GUI split, course.json UX, multi-fragment, multipass, file logs, GPU smoke, CQ↔CRF) live in [remaining-work-plan.md](./remaining-work-plan.md) as R1–R3. Phase 5 smoke/logs remain unchecked on purpose.

### Phase 0 — Repository skeleton

- [x] Package structure:
  - `src/smart_convert_nvenc/` — core
  - `src/smart_convert_nvenc/cli.py`
  - `src/smart_convert_nvenc/gui.py`
  - `docs/` — bilingual
- [x] Dependencies via `uv` (`customtkinter` for GUI)
- [x] Environment check: `ffmpeg`, `hevc_nvenc` (required); `av1_nvenc` optional
- [x] README: FFmpeg / `uv run`

### Phase 1 — Honest benchmark (core)

- [x] Extract source metadata (`ffprobe`: duration, codec, bitrate, size)
- [x] Sampling with offset (default ~25% of duration); multi-fragment average → [remaining-work R2.1](./remaining-work-plan.md)
- [x] Two encode runs on the sample with **identical audio** (`-c:a copy` / `-an` for race)
- [x] Comparison: hybrid VMAF when `libvmaf` present, else size@CQ + disclaimer (decision 1C)
- [x] Threshold: full encode only if projected savings ≥ `min_savings`
- [x] Report: sizes, time, CQ, chosen codec, skip reasons (VMAF scores when enabled)

### Phase 2 — Full encode

- [x] Shared NVENC presets: `p6`/`p7`, `-tune hq`, AQ (multipass/lookahead → [remaining-work R2.2](./remaining-work-plan.md))
- [x] HEVC: `-tag:v hvc1`
- [x] AV1: `.mkv` container
- [x] Final file audio: separate policy (`copy` / AAC / Opus)
- [x] Output with codec suffix; course outbox overwrite option

### Phase 3 — CLI

- [x] `uv run smart-convert path/to/video.mp4`
- [x] Flags: `--sample-sec`, `--offset`, `--min-savings`, `--preset`, `--cq-hevc`, `--cq-av1`, `--dry-run`, `--force-codec`, plus encoder/VMAF/profile/audio
- [x] Non-zero exit code on FFmpeg error / missing required encoders

### Phase 4 — GUI (after stable core)

- [x] Thin wrapper over the same API as CLI
- [x] UI updates only via main thread (`after`)
- [x] Stop = `taskkill` on Windows reliably
- [x] Progress from parsing `out_time` / `time=`
- [x] Do not block UI; one worker + log queue

### Phase 5 — Quality and resilience

> Shipped core vs deferred: smoke and file logs stay open in [remaining-work-plan.md](./remaining-work-plan.md) R3 — Phase 5 is **not** fully closed.

- [x] Unit tests for FFmpeg command assembly (no real encode); coverage ≥90%
- [ ] Optional GPU smoke → [remaining-work R3.2](./remaining-work-plan.md)
- [ ] Logs to file → [remaining-work R3.1](./remaining-work-plan.md); temps use unique `*.conv.<id>.*`
- [x] Handle paths with spaces/Unicode (Windows)

---

## Proposed MVP (minimum viable product)

1. CLI + NVENC core.
2. Sample with offset, `-c:a copy`.
3. Comparison **with an explicit warning** if VMAF is unavailable:  
   either require `libvmaf`, or a temporary “size @ fixed CQ” mode with a disclaimer in the report.
4. Full encode only when savings ≥ threshold.
5. GUI — after MVP.

---

## Open decisions (need agreement)

### Where to mark choices

Fill in the **“Decision log”** table at the end of this section.

Rules:
- In the **Decision** column, write the chosen option (`A` / `B` / short text).
- In the **Status** column, set `accepted` or leave `pending`.
- Optionally add date and comment.
- Until all 4 rows are `accepted`, do not start MVP “blindly”.

---

### Question 1. How to honestly pick the winner: with VMAF or size only?

**Core issue.**  
In the source chat, the winner = “whoever has the smaller file”. But if HEVC CQ=28 and AV1 CQ=32, the smaller file may simply look worse. We need to decide how strictly to measure quality in the first version.

**What VMAF is (in plain terms).**  
A score of “how similar the re-encoded video is to the original” (usually 0–100, higher is better). Computed by FFmpeg with the `libvmaf` filter. Not perfect, but far more honest than comparing megabytes alone.

| Option | What we do | Pros | Cons |
|--------|------------|------|------|
| **A. VMAF required** | Compute VMAF on the sample for HEVC and AV1; winner considers quality and size | Honest codec choice | Needs FFmpeg with `libvmaf`; longer test; more complex code |
| **B. No VMAF first** | Compare size at fixed CQ + report disclaimer: “this is not equal-quality comparison” | Faster MVP | May pick a codec that simply crushed the picture harder |
| **C. Hybrid** | Default size@CQ; if `libvmaf` is present — enable VMAF automatically | Flexible | Two behavior modes, harder to explain to the user |

**Affects:** Phase 1 (benchmark core), dependencies, test speed, trust in the “winner”.

**Recommendation for course archive:** **B** or **C**.  
For screencast/slides, a stable “good enough” CQ and running thousands of files matter more than perfect VMAF on each.  
**Accepted:** **C** (hybrid) — see decision log #1 (`--vmaf auto|off|on`).

---

### Question 2. Build a GUI immediately or CLI first?

**Core issue.**  
The chat asked for a GUI. But a GUI without a stable core usually becomes copy-pasted bugs (stop does not kill ffmpeg, UI freezes, fake progress).

| Option | What we do | Pros | Cons |
|--------|------------|------|------|
| **A. CLI only in MVP** | Run like `uv run smart-convert video.mp4` | Faster to a working result; easier debugging | No Browse button / pretty window |
| **B. CLI + GUI at once** | Parallel CustomTkinter window | Feels like “a program” immediately | Longer; risk fixing UI instead of codec selection logic |
| **C. CLI now, GUI next** | Core+CLI first, GUI as thin wrapper over same API | Best balance | GUI not on day one |

**Affects:** Phases 3–4, dependencies (`customtkinter`), timeline.

**Recommendation for course archive:** **C** (CLI now → GUI next).  
For hundreds/thousands of files, reliable batch CLI comes first; a window is convenient on top of a working core.

---

### Question 3. GPU only (NVENC) or CPU fallback too?

**Core issue.**  
You have RTX 4060 Ti — NVENC is fast. But software codecs (`libx265`, `libsvtav1`) usually compress **more efficiently** (smaller file at the same visual quality), just much slower.

| Option | What we do | Pros | Cons |
|--------|------------|------|------|
| **A. NVENC only** | Compare `hevc_nvenc` vs `av1_nvenc` | Simple; fast; matches project name | Not the smallest possible file |
| **B. NVENC + CPU fallback** | If NVENC missing / broken — try x265/SVT-AV1 | Works on PC without suitable GPU | More code, presets, tests |
| **C. NVENC and CPU as modes** | User picks: `gpu` / `cpu` / `auto` | Maximum flexibility | Largest scope |

**Affects:** Phases 1–2, environment check, CLI flags, encode time.

**Recommendation for course archive:** **A (NVENC only)** in MVP.  
Archive volume is large — speed beats the last 10–20% compression from CPU.  
**Accepted:** **C** (`gpu` / `cpu` / `auto`) — see decision log #3.

---

### Question 4. What to do with audio in the final file?

**Core issue.**  
Two separate moments:

1. **On the sample test**, better not touch audio (`-c:a copy`), otherwise AAC vs Opus skews video codec comparison. Already fixed in plan principles.
2. **In the final full file** — separate choice: copy track as-is or re-encode to save space.

| Option | What we do in full encode | Pros | Cons |
|--------|---------------------------|------|------|
| **A. `copy` by default** | Do not re-encode audio | No audio quality loss; faster; cleaner view of video savings | If source audio is huge (PCM/DTS), file stays heavy |
| **B. Always re-encode** | e.g. AAC 128k or Opus 128k | Extra space savings | Extra audio quality loss; part of “win” is audio, not video |
| **C. `copy`, but with option** | Default copy; flag like `--audio aac:128k` | Flexible | Slightly more settings |

**Affects:** Phase 2, final file size, CLI/GUI flags.

**Recommendation for course archive:** **C**.  
Default `copy` (do not ruin audio or distort video savings). Option to re-encode speech to AAC/Opus ~96–128k — often noticeable savings on courses with “fat” source audio.

---

### Decision log

> Mark choices here. While status is `pending`, the decision is not locked in.

| # | Question | Options | Decision | Status | Date | Comment |
|---|----------|---------|----------|--------|------|---------|
| 1 | Winner selection metric | A VMAF required / B no VMAF + disclaimer / C hybrid | C | accepted | 2026-07-26 | Was B for MVP; F6.3 landed hybrid (`vmaf=auto`) |
| 2 | CLI vs GUI | A CLI only / B CLI+GUI at once / C CLI now, GUI next | C | accepted | 2026-07-24 | CLI first, GUI next |
| 3 | NVENC vs CPU | A NVENC only / B + CPU fallback / C gpu/cpu/auto modes | C | accepted | 2026-07-26 | Was A for MVP; F6.4 landed `gpu`/`cpu`/`auto` |
| 4 | Final audio | A copy / B always re-encode / C copy + option | C | accepted | 2026-07-24 | copy by default; `--audio` optional |
| 5 | Course metadata | long folder name / tagged brackets / `course.json` | `course.json` + short name | accepted | 2026-07-24 | ADR-0002: metadata and root marker in `course.json`; path without pub/by; JSON optional |

**Example filled row:**

| 2 | CLI vs GUI | A / B / C | C | accepted | 2026-07-24 | GUI after working CLI |

---

## Roadmap for course archive (on top of phases)

| Stage | What it gives for “free disk” goal | Status |
|-------|-------------------------------------|--------|
| Single-file MVP | One file → test → NVENC compress | done (`smart-convert`) |
| Folder pipeline | `courses/inbox` → `tmp` → `outbox` (+ non-video) | done ([ADR-0001](./adr/0001-course-inbox-outbox-tmp.md)) |
| Course names / metadata | short folder name + opt. `course.json` | locked in ([ADR-0002](./adr/0002-course-folder-naming.md)) |
| GUI | Course queue, logs, progress, Windows guard | done (`smart-convert-gui`) |
| Resilience / reports from video_converter experience | Stop/kill, temp, MiB/hour, tests… | done ([feature-port-plan.md](./feature-port-plan.md) F1–F6) |
| Duplicates | Find copies, report only (no delete) | done (`smart-convert duplicates`) |
| “Course” profile | Named presets in `profiles.toml` | done (`--profile`) |
| Encoder modes | gpu / cpu / auto | done (`--encoder`) |
| Hybrid VMAF | Quality floor when libvmaf present | done (`--vmaf`) |
| Pack exe | Standalone Windows/Linux zip | experimental ([RELEASES.md](./RELEASES.md)) |

### Phase B — Course pipeline (per ADR-0001)

- [x] Directories `courses/inbox`, `courses/outbox`, `courses/tmp` + README (English-only)
- [x] ADR-0001 accepted (defaults in project + CLI/env override)
- [x] Path resolution: project-root defaults, `--courses-root` / `--inbox` / `--outbox` / `--tmp`, env
- [x] Walk videos in `inbox/<course>/`, encode in `tmp/<course>/`
- [x] Preserve structure and **all non-video** when publishing to `outbox/`
- [x] Decision at **whole course** level (total size)
- [x] If not worthwhile — `move` source `inbox → outbox`, clean `tmp`
- [x] If worthwhile — assemble mixed tree (compressed + original videos + non-video)
- [x] Name conflict in `outbox/` → overwrite by default; opt out with `--no-overwrite-outbox` / GUI checkbox
- [x] CLI: `smart-convert-course` [name]
- [x] GUI: `smart-convert-gui`
- [x] Recommendation: inbox/outbox/tmp on same volume (documented in ADR-0001)
## Out of scope (for now)

- Cloud upload / streaming profiles
- AMD/Intel QSV support in first version
- Automatic duplicate deletion without report and confirmation (dangerous)
- Finishing the old `video_converter` repository (reference only)

---

## Next step

1. ~~MVP / pipeline / GUI / Windows guard / feature-port F1–F6 / v0.1.8~~ — done.
2. ~~R1 (GUI split + course.json + profile picker + richer duplicates)~~ — done.
3. Execute [remaining-work-plan.md](./remaining-work-plan.md): **R2** (encode), then **R3** (ops/release).
