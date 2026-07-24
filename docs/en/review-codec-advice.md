# Review: codec advice and scripts from chat

Русский: [../ru/review-codec-advice.md](../ru/review-codec-advice.md).

Review date: 2026-07-24  
Source: [chat-optimal-mpeg4-codec.md](./chat-optimal-mpeg4-codec.md)

## Verdict

Direction is broadly correct: HEVC/AV1, CRF/CQ, HandBrake/FFmpeg, NVENC on RTX 40xx — a reasonable cheat sheet.

As a method for choosing “where compression is more efficient at the same quality” — **invalid**. Scripts are fine as a pipeline prototype, but not as a quality benchmark.

---

## What is correct

| Claim | Assessment |
|-------|------------|
| MPEG-4 is an umbrella (often H.264 or Part 2 / Xvid/DivX) | Correct |
| For strong compression — HEVC and AV1 | Correct |
| RTX 4060 Ti: has `hevc_nvenc` and `av1_nvenc` | Correct |
| Software: CRF + preset slow/slower | Correct |
| NVENC: `-rc vbr -cq … -b:v 0`, presets `p1–p7`, `-tune hq` | Correct |
| `-tag:v hvc1` for Apple/Safari (HEVC) | Correct |
| AV1 + Opus in `.mkv` — practical container | Correct |
| Idea “sample → compare → full encode” | Reasonable as an idea |
| GUI on CustomTkinter — fine prototype | OK as draft |

Figures like “AV1 20–30% smaller than HEVC” — a guide for **software** encoders at comparable quality. For NVENC the gap is usually smaller; NVENC is weaker than x265 / SVT-AV1 on bits per quality.

---

## Critical methodology problems

### 1. They compare size, not quality

CQ/CRF scales differ across codecs.  
`H265_CQ=28` and `AV1_CQ=32` do not mean the same picture.  
The winner by MiB may simply have crushed the video harder.

Without VMAF/SSIM (or at least visual comparison) this is not “efficiency”, but “who made the smaller file”.

### 2. Audio ruins the test

In samples: HEVC → AAC, AV1 → Opus.  
Part of the size difference is audio, not video.

For an honest video test: `-c:a copy` or the same audio codec/bitrate in both runs.

### 3. First 30 seconds — bad sample

Intro/titles are often unrepresentative.  
Better: middle of file, several fragments, or `-ss` at 10–25% of duration.

### 4. No comparison to source

You can “win” with a codec that is still larger than the original.  
Need a threshold: full encode only if savings are meaningful (e.g. >10–15%).

### 5. Myth “quality stays the same”

Repeated lossy encoding always loses something (generation loss).  
If the source is already well compressed (HEVC/AV1), gain is often tiny or negative. The chat barely mentions this.

---

## Notes on NVENC and GUI

| Topic | Assessment |
|-------|------------|
| “NVENC has no CRF, has `-cq`” | Simplification, OK for users |
| AQ (`spatial_aq` / `temporal_aq`) | Useful for HEVC; for AV1 depends on FFmpeg version |
| `main10` only for HEVC | Asymmetric; not always needed on 8-bit source |
| `-hwaccel auto` | Usually works, but not zero-copy; explicit CUDA pipeline is more reliable |
| Stop in GUI | `terminate` is unreliable |
| UI updates from worker thread | Tk race/glitch risk — need `after()` |
| Progress bar | Steps 10%/30%/50%, not real encode progress |
| 16 GB VRAM | Barely affects NVENC quality/speed |

---

## What to improve first

1. Quality metric on sample (VMAF) **or** fixed target bitrate and quality comparison.
2. Identical audio pipeline in test (`copy`).
3. Sample not from start + optionally 2–3 fragments.
4. Compare to original size; do not encode everything without gain.
5. Multipass / lookahead for NVENC; CPU option (x265/SVT-AV1) vs GPU.
6. In GUI: reliable process kill, UI via `after()`, progress from `time=` / `out_time`.

---

## One-line summary

The chat is a valid popular cheat sheet; the proposed “smart” codec choice by sample size at different CQ and different audio systematically misleads.
