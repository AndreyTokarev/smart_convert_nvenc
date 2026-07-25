from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import tkinter as tk
from tkinter import messagebox

from .course import convert_course, iter_videos, tree_size
from .course_meta import load_course_meta
from .ffmpeg_runner import FFmpegCancelled, kill_active_subprocesses
from .gui_course_list import refresh_courses, select_all, select_none, selected_courses
from .gui_theme import COLORS
from .models import ConvertSettings, VideoCodec
from .probe import ToolError
from .profiles import get_profile
from .progress import ProgressUpdate
from .session import SessionStats, format_gib_or_mib
from .temp_paths import cleanup_conversion_temps

if TYPE_CHECKING:
    from .gui import App


def convert_settings(app: App) -> ConvertSettings:
    """Build ConvertSettings: profile defaults + widget overrides (CLI parity)."""
    profile_name = app.profile_var.get().strip() or "default"
    profile = get_profile(profile_name)
    codec_raw = app.codec_var.get()
    force = None if codec_raw == "auto" else VideoCodec(codec_raw)
    enc_raw = app.encoder_var.get().strip().lower()
    if enc_raw not in {"gpu", "cpu", "auto"}:
        enc_raw = "gpu"
    vmaf_raw = app.vmaf_var.get().strip().lower()
    if vmaf_raw not in {"off", "auto", "on"}:
        vmaf_raw = "auto"
    return profile.to_convert_settings(
        sample_seconds=float(app.sample_var.get()),
        min_savings=float(app.min_savings_var.get()),
        hevc_cq=int(app.cq_hevc_var.get()),
        av1_cq=int(app.cq_av1_var.get()),
        preset=app.preset_var.get().strip(),
        encoder=enc_raw,
        vmaf=vmaf_raw,
        force_codec=force,
        skip_same_codec=bool(app.skip_same_codec_var.get()),
    )


def emit_progress(app: App, update: ProgressUpdate) -> None:
    offset = app._job_course_offsets.get(update.course_name, 0)
    done_before = offset + (update.video_index - 1)
    overall_units = done_before + update.file_fraction
    total = max(1, app._job_total_videos)
    job_frac = overall_units / total
    phase = update.phase.replace("_", " ")
    speed_bit = (
        f"  {update.ffmpeg_speed:.1f}x" if update.ffmpeg_speed is not None else ""
    )
    file_text = (
        f"File: {update.video_name}  ({update.video_index}/{update.videos_in_course})  "
        f"{phase}  {update.file_fraction * 100:.0f}%{speed_bit}"
    )
    job_text = (
        f"Job: {int(overall_units)}/{total} videos  ({job_frac * 100:.0f}%)  "
        f"course: {update.course_name}"
    )
    app._progress_q.put((update.file_fraction, job_frac, file_text, job_text))


def set_running(app: App, running: bool) -> None:
    state_idle = "normal" if not running else "disabled"
    state_run = "normal" if running else "disabled"
    app.start_btn.configure(state=state_idle)
    app.start_all_btn.configure(state=state_idle)
    app.stop_btn.configure(state=state_run)
    for widget in app._path_widgets:
        try:
            widget.configure(state=state_idle)
        except tk.TclError:
            pass


def refresh_savings_labels(app: App) -> None:
    stats = app._session_stats
    last = stats.last_course()
    if last is None:
        app.last_course_label.configure(text="Last course: —")
    else:
        app.last_course_label.configure(
            text=(
                f"Last: {format_gib_or_mib(last.freed_bytes)} freed "
                f"({last.ratio * 100:.1f}%)"
            )
        )
    app.session_freed_label.configure(
        text=f"Session freed: {format_gib_or_mib(stats.freed_bytes)}"
    )
    if stats.courses:
        app.session_rate_label.configure(
            text=f"{stats.ratio * 100:.1f}% · {stats.mib_per_hour:.0f} MiB/h"
        )
    else:
        app.session_rate_label.configure(text="—")


def start(app: App) -> None:
    courses = selected_courses(app)
    if not courses:
        messagebox.showwarning("Smart Convert", "Select at least one course.")
        return
    run(app, courses)


def start_all(app: App) -> None:
    refresh_courses(app)
    courses = [path for _, path in app._course_vars]
    if not courses:
        messagebox.showwarning("Smart Convert", "Inbox is empty.")
        return
    select_all(app)
    run(app, courses)


def stop(app: App) -> None:
    app._stop.set()
    killed = kill_active_subprocesses()
    if killed:
        app._app_log(f"Stop: killed {killed} FFmpeg process tree(s)")
    else:
        app._app_log("Stop requested...")
    app.status.configure(text="Stopping...", text_color="#e0a84c")


def run(app: App, courses: list[Path]) -> None:
    if app._worker and app._worker.is_alive():
        messagebox.showwarning("Smart Convert", "Already running.")
        return
    courses = sorted(courses, key=lambda p: (-tree_size(p), p.name.lower()))

    try:
        settings = convert_settings(app)
        app._persist_settings()
    except ValueError as exc:
        messagebox.showerror("Smart Convert", f"Bad settings: {exc}")
        return
    except OSError as exc:
        messagebox.showerror("Smart Convert", f"Cannot save settings: {exc}")
        return

    app._stop.clear()
    set_running(app, True)
    app._session_stats = SessionStats()
    refresh_savings_labels(app)
    app._job_total_videos = sum(len(iter_videos(c)) for c in courses)
    app._job_completed_videos = 0
    app._job_course_offsets = {}
    offset = 0
    for course in courses:
        app._job_course_offsets[course.name] = offset
        offset += len(iter_videos(course))

    app.file_bar.set(0)
    app.job_bar.set(0)
    app.file_progress_label.configure(text="File: starting...")
    app.job_progress_label.configure(
        text=f"Job: 0/{app._job_total_videos} videos (0%)"
    )
    app.status.configure(text=f"Running 0/{len(courses)}...", text_color=COLORS["accent"])
    app.ff_live.configure(text="starting...")
    app._app_log("=" * 60)
    app._app_log(
        f"Queue: {len(courses)} course(s), {app._job_total_videos} videos, sequential"
    )
    try:
        hwnd = int(app.winfo_id())
    except tk.TclError:
        hwnd = None
    app._session_guard.start(hwnd)
    app._app_log(
        "Windows guard ON: sleep blocked, pending reboot/shutdown aborted while job runs"
    )

    def worker() -> None:
        try:
            for i, course in enumerate(courses, start=1):
                if app._stop.is_set():
                    app._app_log("Stopped by user.")
                    break
                app.after(
                    0,
                    lambda i=i, n=len(courses), name=course.name: app.status.configure(
                        text=f"Running {i}/{n}: {name}",
                        text_color=COLORS["accent"],
                    ),
                )
                app._ff_log(f"--- course: {course.name} ---", replace_live=False)

                try:
                    result = convert_course(
                        course,
                        app.paths,
                        settings,
                        race_once=True,
                        overwrite_outbox=bool(app.overwrite_outbox_var.get()),
                        log=app._app_log,
                        on_ffmpeg_progress=lambda line: app._ff_log(line, replace_live=True),
                        on_progress=lambda update: emit_progress(app, update),
                        should_stop=app._stop.is_set,
                    )
                    meta = load_course_meta(course)
                    item = app._session_stats.add_course(
                        result.name,
                        result.original_size,
                        result.final_size,
                        title=meta.title if meta and meta.title.strip() else None,
                        publishers=meta.publishers if meta else (),
                        authors=meta.authors if meta else (),
                        year=meta.year if meta else None,
                    )
                    app._app_log(
                        f"Course result: {result.name}: "
                        f"{format_gib_or_mib(result.original_size)} → "
                        f"{format_gib_or_mib(result.final_size)} "
                        f"(freed {format_gib_or_mib(item.freed_bytes)}, "
                        f"{item.ratio * 100:.1f}%)"
                    )
                    app.after(0, lambda: refresh_savings_labels(app))
                except FFmpegCancelled:
                    app._app_log("Stopped by user.")
                    break
                except RuntimeError as exc:
                    if "Stopped by user" in str(exc):
                        app._app_log("Stopped by user.")
                        break
                    raise
            else:
                app._app_log("All queued courses finished.")
                app._progress_q.put(
                    (
                        1.0,
                        1.0,
                        "File: done",
                        f"Job: {app._job_total_videos}/{app._job_total_videos} videos (100%)",
                    )
                )
            if app._session_stats.courses:
                app._app_log(app._session_stats.summary_line())
                app.after(0, lambda: refresh_savings_labels(app))
        except (
            ToolError,
            FileNotFoundError,
            FileExistsError,
            ValueError,
            OSError,
            RuntimeError,
            FFmpegCancelled,
        ) as exc:
            if isinstance(exc, FFmpegCancelled):
                app._app_log("Stopped by user.")
            else:
                err_text = str(exc)
                app._app_log(f"ERROR: {err_text}")
                app.after(
                    0,
                    lambda msg=err_text: messagebox.showerror("Smart Convert", msg),
                )
        finally:
            cleanup_conversion_temps(app.paths.tmp)
            app.after(0, app._session_guard.stop)
            app.after(0, lambda: app._app_log("Windows guard OFF"))
            app.after(0, lambda: set_running(app, False))
            app.after(0, app.refresh_courses)
            app.after(
                0,
                lambda: app.status.configure(text="Ready", text_color=COLORS["ok"]),
            )
            app.after(0, lambda: app.ff_live.configure(text="idle"))

    app._worker = threading.Thread(target=worker, daemon=True)
    app._worker.start()
