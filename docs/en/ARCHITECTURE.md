# Architecture — smart_convert_nvenc

Русский: [../ru/ARCHITECTURE.md](../ru/ARCHITECTURE.md).

## System goal

Compress a video-course archive with NVIDIA NVENC so that:

1. disk space is reclaimed at “good enough” quality for slides + speech;
2. work units are **courses** (folders), not stray files;
3. inbox is never left half-broken by a partial publish;
4. the whole course is not duplicated on disk during encoding.

## Data flow

```text
                    ┌─────────────┐
   course folder →  │ courses/    │
                    │  inbox/     │
                    └──────┬──────┘
                           │ list + probe + encode
                           ▼
                    ┌─────────────┐
                    │ courses/    │
                    │  tmp/       │  unique *.conv.<id>.* then promote
                    └──────┬──────┘
                           │ assemble OR pass-through original
                           ▼
                    ┌─────────────┐
                    │ courses/    │
                    │  outbox/    │
                    └─────────────┘
```

Accepted ADRs:

- [ADR-0001](./adr/0001-course-inbox-outbox-tmp.md) — folder pipeline
- [ADR-0002](./adr/0002-course-folder-naming.md) — short names + optional `course.json`

## Layers

```text
CLI / GUI
    ↓
course.convert_course / pipeline.convert_video
    ↓
encode.encode_file → ffmpeg_runner.run_ffmpeg
    ↓
probe / paths / temp_paths / windows_guard / session
```

GUI and CLI share one core — no duplicated FFmpeg argv construction.

## Product decisions

| Topic | Choice | Why |
|-------|--------|-----|
| Race metric | size@CQ + disclaimer | Fast, no VMAF; fine for courses |
| UI | CLI first, then CustomTkinter | MVP speed |
| Encode | NVENC only | Throughput on RTX |
| Audio | copy by default | Protect speech; don’t skew video savings |
| Replacement | outbox, not in-place | Safer rollback / clearer flow |

## Cancel & reliability

1. Active `Popen` processes are registered.
2. Stop / window close → `taskkill /F /T /PID`.
3. Encodes write `name.conv.<id>.ext`, then promote to final.
4. Leftover `*.conv.*` under tmp are cleaned on start/end.
5. On course failure, tmp is removed; partial outbox is not left behind.

## Skip already-encoded

`already_target_codec()` maps ffprobe names:

- auto → skip if already HEVC or AV1;
- forced/locked → skip only on match.

## Session stats

`session.SessionStats` aggregates original/final sizes → freed bytes, ratio, MiB/h for GUI/logs.

## Testing

Unit tests mock subprocess/ffmpeg. Coverage gate 90% excluding `gui.py`.

## Extension points

Safe growth without breaking ADR-0001:

- consume `course.json` in GUI/reports;
- CQ profiles via TOML;
- duplicate scan using JSON title/publishers;
- optional VMAF hybrid later.
