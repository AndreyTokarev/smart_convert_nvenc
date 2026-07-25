# User Guide — smart_convert_nvenc

Detailed English documentation. Русский: [../ru/USER_GUIDE.md](../ru/USER_GUIDE.md).

## 1. Why this project exists

A personal (now open-source) tool to **free disk space** from a large **video course archive**: screen recordings, slides, and speech.

Typical pain:

- courses consume hundreds of GB / TB;
- sources are often fat H.264 or casually high bitrate;
- for learning you need readable slides and clear speech — not cinema Blu-ray quality;
- you must process **whole course folders** (video + PDF + tabs + mp3), not isolated files.

**smart_convert_nvenc** compresses video with **NVIDIA NVENC** (hardware encode), decides at the **course** level, moves results to an outbox, and avoids duplicating entire courses on disk during work.

Built **from scratch** as a fast MVP, informed by an earlier personal converter, but with a different product model: not in-place file replacement — an `inbox → tmp → outbox` pipeline.

License: **MIT** — use, modify, redistribute freely.

## 2. What it does today

| Feature | Description |
|---------|-------------|
| HEVC vs AV1 sample race | Short fragment size comparison at configured CQ; winner gets full encode |
| Min-savings threshold | Keeps compressed file/course only if savings beat the threshold |
| Course pipeline | First-level inbox folder = one course; non-video preserved |
| Single-file CLI | `smart-convert` |
| Course CLI | `smart-convert-course` |
| GUI | Course queue, paths, logs, progress, session savings |
| Hard Stop | Kills FFmpeg process tree (`taskkill /T`) |
| Skip same codec | Skips already HEVC/AV1 (configurable) |
| No-video pass-through | PDF-only course → outbox immediately |
| Windows guard | Blocks sleep; periodic `shutdown /a` |
| GUI settings persist | `%APPDATA%\smart_convert_nvenc\settings.json` |
| Tests | `pytest` + ≥90% coverage (no GPU required) |

## 3. What it does not do (yet / by design)

- VMAF / equal-quality codec comparison (size@CQ disclaimer instead)
- Auto-renaming course folders
- Duplicate detection (planned)
- Packaged `.exe` installer (planned)
- AMD/Intel hardware encode; CQ↔CRF recalibration for CPU vs NVENC

## 4. Requirements

- **OS:** Windows 10/11 (primary target)
- **Python:** 3.12+
- **Package manager:** [uv](https://github.com/astral-sh/uv)
- **FFmpeg** on `PATH` (when running from source):
  - **GPU (default):** `hevc_nvenc` and `av1_nvenc`
  - **CPU / auto-fallback:** `libx265` and `libsvtav1`
  - Release zips (Win/Linux) already ship FFmpeg under `ffmpeg/bin/`; optional override: `SMART_CONVERT_FFMPEG_DIR`
- **GPU (optional):** NVIDIA with NVENC; **AV1 encode** typically needs RTX 40-series
- Current NVIDIA driver (when using GPU)

```powershell
ffmpeg -hide_banner -encoders | findstr /i "nvenc libx265 libsvtav1"
ffprobe -version
```

## 5. Install

**Supported path:** clone the repo and run with `uv` (from source). Standalone Release zips exist but are **early / untested** — see [RELEASES.md](./RELEASES.md).

```powershell
git clone https://github.com/AndreyTokarev/smart_convert_nvenc.git
cd smart_convert_nvenc
uv sync
uv sync --group dev   # tests / contrib
```

| Command | Purpose |
|---------|---------|
| `uv run smart-convert` | One video file |
| `uv run smart-convert-course` | Courses from inbox |
| `uv run smart-convert-gui` | Desktop UI |

Three scripts for source installs; the **release zip** ships a single `smart-convert` with the same modes — see [RELEASES.md](./RELEASES.md) (“Why three commands…”).

## 6. Folder model (ADR-0001)

Default layout next to the repo:

```text
courses/
  inbox/     ← drop course folders here
  tmp/       ← temporary encodes (cleaned)
  outbox/    ← result (compressed or original as-is)
```

**Unit of work** = first-level folder under `inbox/`.

Course algorithm:

1. Measure full tree size.
2. Per video: sample race (or forced codec) → full encode under `tmp/<course>/…` if worth it.
3. Candidate size = chosen videos + all non-video files.
4. If course worth it → assemble into `outbox` (videos from tmp, other files moved from inbox).
5. If not → `move inbox/Name → outbox/Name`.
6. On mid-flight failure: leave course in inbox; never publish a partial outbox tree.

If `outbox/Name` already exists, it is **removed and replaced by default** (GUI: «Overwrite existing outbox course»; CLI: `--no-overwrite-outbox` to fail instead).

Overrides:

- CLI: `--courses-root`, `--inbox`, `--outbox`, `--tmp`
- Env: `SMART_CONVERT_*`
- GUI: Folders panel + saved settings

Keep inbox/outbox/tmp on **one volume** so `move` stays cheap.

## 7. Naming & metadata (ADR-0002)

Preferred **short** folder names:

```text
[0000] 20 Sick Licks
[2024] Complete Jazz Guitar
```

`[0000]` means unknown year. Do not stuff publisher/author into the path (MAX_PATH).

Optional root file `course.json`:

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

Encode does **not** require JSON today; it is preserved with the course. Later: root marker + metadata for reports/duplicates.

Any folder name is valid — the tool **never renames**.

## 8. Codec selection

1. Take a sample (default ~20–30s, offset ~25% of duration).
2. Encode HEVC (default CQ 28) and AV1 (CQ 32) on the sample with **video only** (`-an`) so the size race is not skewed by audio and MPEG-TS seek stays reliable.
   - GPU mode: HEVC uses `hevc_nvenc`. AV1 uses `av1_nvenc` when present (bundled n8.1 includes it); otherwise **libsvtav1** (CPU) as fallback.
3. Smaller sample wins; size is projected to full duration.
4. If projected savings < `min_savings` → skip full encode for that file.
5. After full encode, re-check real size.
6. Course-level threshold: `min_course_savings`.

**Disclaimer:** size@different CQ is **not** equal quality. Good enough for slide courses; VMAF is not in the MVP.

Default **race once** per course: first compressed video locks the codec for the rest (faster).

Final audio defaults to **`copy`**. Optional `--audio aac:128` / `opus:96`.

## 9. GUI

```powershell
uv run smart-convert-gui
```

Starts **maximized**.

Blocks:

- **Folders** — inbox/outbox/tmp, Browse, Courses root, Apply, Defaults
- **Courses** — list, Refresh / Select all / Open inbox|outbox
- **Settings** — sample, savings, CQ, preset, codec, encoder (gpu/cpu/auto), Skip if already HEVC/AV1, Overwrite existing outbox course (on by default)
- **Progress** — file/job bars + Last / Session freed / % · MiB/h
- **App log / FFmpeg** — journal + live ffmpeg line

Settings file:

`%APPDATA%\smart_convert_nvenc\settings.json`

**Stop** hard-kills the current FFmpeg tree.

Encoder modes: `gpu` (NVENC only, default), `cpu` (libx265 / libsvtav1), `auto` (NVENC if present, else CPU).

Named presets live in `src/smart_convert_nvenc/data/profiles.toml` (`default`, `course`). Use `--profile`; other CLI flags override the profile.

## 10. CLI examples

```powershell
uv run smart-convert lesson.mp4
uv run smart-convert lesson.mp4 --profile course
uv run smart-convert lesson.mp4 --dry-run --force-codec hevc
uv run smart-convert lesson.mp4 --encoder auto
uv run smart-convert lesson.mp4 --encoder cpu --force-codec hevc
uv run smart-convert lesson.mp4 --audio opus:96 --min-savings 0.15
uv run smart-convert lesson.mp4 --reencode-same-codec

uv run smart-convert-course
uv run smart-convert-course --profile course
uv run smart-convert-course "My Course Name"
uv run smart-convert-course --encoder auto
uv run smart-convert-course --courses-root E:\archive\courses
uv run smart-convert-course --race-each
```

After a course batch, Markdown totals land in `courses/session-report.md` (override with `--session-report PATH`, skip with `--no-session-report`).

### Duplicates (report only)

```powershell
uv run smart-convert duplicates
uv run smart-convert duplicates --videos-only -o dupes.md
uv run smart-convert-duplicates E:\archive\courses\inbox E:\archive\courses\outbox --min-size 0
```

Scans for exact file copies (same size + SHA-256) and course folders with the same name. **Never deletes.**

## 11. Environment variables

| Variable | Meaning |
|----------|---------|
| `SMART_CONVERT_COURSES_ROOT` | Root containing inbox/outbox/tmp |
| `SMART_CONVERT_INBOX` | Inbox path |
| `SMART_CONVERT_OUTBOX` | Outbox path |
| `SMART_CONVERT_TMP` | Tmp path |
| `SMART_CONVERT_APPDATA` | Settings root (tests / portable) |
| `SMART_CONVERT_FFMPEG_DIR` | Directory with `ffmpeg`/`ffprobe` (or `…/bin`); overrides bundled + PATH |

## 12. Tests

```powershell
uv sync --group dev
uv run pytest --cov=smart_convert_nvenc --cov-report=term-missing
```

No GPU required. `gui.py` is omitted from coverage metrics.

## 13. Module map

See also [ARCHITECTURE.md](./ARCHITECTURE.md).

| Module | Role |
|--------|------|
| `profiles.py` | Load named presets from `data/profiles.toml` |
| `duplicates.py` | Exact-file + same-name course duplicate report |
| `pipeline.py` | Per-file race + encode |
| `course.py` | Course walk + outbox assemble |
| `encode.py` | NVENC argv, temps, hwaccel retry |
| `ffmpeg_runner.py` | Popen registry, cancel, taskkill |
| `probe.py` | ffprobe + env validation |
| `gui.py` / `gui_settings.py` | UI + persistence |
| `session.py` | Freed bytes / % / MiB/h |
| `windows_guard.py` | Sleep / reboot guard |
| `temp_paths.py` | `*.conv.<id>.*` |
| `paths.py` | Path resolution |

## 14. Safety

- The tool **moves and re-encodes** media. Back up anything precious.
- MIT “AS IS” — no warranty.
- Do not commit course media (default `courses/**` content is gitignored).

## 15. Roadmap (high level)

- Later: VMAF / hybrid quality metric

Details: [feature-port-plan.md](./feature-port-plan.md), [refactoring-plan.md](./refactoring-plan.md).
