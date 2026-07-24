# Community post (English) — for VK / open-source announcement

Copy-paste ready. Feel free to trim. Replace `<REPO_URL>` before publishing.

---

**smart_convert_nvenc — free (MIT) tool to reclaim disk space from video course archives (NVIDIA NVENC)**

Hey everyone 👋

I put together a small open-source project on a bit of a **rush / MVP timeline**, but it’s already useful for a real problem I hit myself:

> Huge folders of online courses (screen + slides + speech) eating hundreds of GB… while you still need the lessons readable, not “mastering-grade” video.

### What it is

**smart_convert_nvenc** compresses course videos with **NVIDIA hardware encoders** (NVENC):

- races **HEVC vs AV1** on a short sample (size @ CQ — with an honest disclaimer that this is not equal-quality VMAF);
- only keeps a full encode if projected / actual savings beat a threshold;
- works on **whole course folders** (`inbox → tmp → outbox`), keeping PDFs, tabs, mp3s, etc.;
- has **CLI + a simple GUI** (CustomTkinter);
- hard-stops FFmpeg cleanly on Windows;
- skips files that are **already HEVC/AV1**;
- shows session **freed space / % / MiB/h**;
- tries not to duplicate entire courses on disk while working.

License: **MIT** — free to use, fork, modify, ship.

Repo: `<REPO_URL>`

### Why I built it

I maintain a large personal archive of video courses. Buying another drive forever is boring. Re-encoding by hand in HandBrake for every lesson is worse. I wanted something that:

1. understands a **course** as the unit of work;
2. is fast because it uses the **GPU**;
3. is safe enough for a personal archive (outbox model, no silent in-place overwrite of the only copy mid-job);
4. can run unattended for a while on Windows without the PC sleeping / reboot timers sneaking in.

This is **not** a polished commercial product. It’s a practical tool I needed, written quickly, cleaned up enough to share, with docs in **Russian and English**, tests, and ADRs for the folder pipeline.

### Who might care

- people with fat course / lecture / tutorial libraries on NVMe/HDD;
- anyone with an **RTX** (40-series especially, if you want AV1 encode) and FFmpeg with NVENC;
- open-source folks who want a small, readable Python + uv codebase rather than a giant media suite.

### Honest limitations (MVP)

- Windows-first;
- NVENC-only (no CPU fallback yet);
- codec race is **size-based**, not VMAF;
- no duplicate finder yet;
- no fancy installer/exe pack yet.

If that still sounds useful — clone it, break it, send PRs, or just tell me what you’d change first.

Thanks — and may your `courses/outbox` be smaller than your `inbox`. 💾

`#opensource` `#python` `#ffmpeg` `#nvenc` `#hevc` `#av1` `#diskspace`

---

## Short VK-friendly version (optional)

Built a MIT-licensed MVP to shrink video **course archives** with NVIDIA NVENC (HEVC vs AV1 sample race → full encode only if it saves space). Course folders go `inbox → outbox`, GUI + CLI, hard Stop, skip already-HEVC/AV1, session “freed MiB” stats. Written fast for my own TB-sized library — sharing in case it helps others with RTX + FFmpeg. Repo: `<REPO_URL>`
