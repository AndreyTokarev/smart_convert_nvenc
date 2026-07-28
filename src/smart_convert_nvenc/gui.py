from __future__ import annotations

import queue
import threading
from pathlib import Path

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from . import __version__
from .ffmpeg_runner import kill_active_subprocesses
from .gui_course_list import refresh_courses as refresh_course_list
from .gui_course_list import select_all as select_all_courses
from .gui_course_list import select_none as select_none_courses
from .gui_job import (
    emit_progress,
    refresh_savings_labels,
    run as run_job,
    set_running,
    start as start_job,
    start_all as start_all_job,
    stop as stop_job,
)
from .gui_layout import build_ui
from .gui_paths import (
    apply_paths,
    browse_inbox,
    browse_outbox,
    browse_tmp,
    open_inbox,
    open_outbox,
    pick_courses_root,
    reset_paths_defaults,
)
from .gui_settings import GuiSettings, default_settings_path, load_gui_settings, save_gui_settings
from .gui_theme import APP_LOG_MAX_LINES, COLORS, FF_LOG_MAX_LINES, configure_appearance
from .models import EncoderBackend
from .paths import ensure_long_paths
from .probe import ToolError, validate_environment
from .profiles import get_profile, list_profile_names
from .progress import ProgressUpdate, clamp01, trim_textbox_line_count
from .session import SessionStats
from .temp_paths import cleanup_conversion_temps
from .windows_guard import WindowsSessionGuard

configure_appearance()


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Smart Convert NVENC {__version__}")
        self.geometry("1200x860")
        self.minsize(1000, 720)
        self.configure(fg_color=COLORS["bg"])
        # CustomTkinter resets state on Windows mainloop; delay maximize.
        self.after(1, self.state, "zoomed")

        self._settings_path = default_settings_path()
        self._gui_settings = load_gui_settings(self._settings_path)
        self.paths = self._gui_settings.course_paths()
        self.paths.ensure()
        removed = cleanup_conversion_temps(self.paths.tmp)
        self._env_ok_lines: list[str] = []
        try:
            enc = self._gui_settings.encoder if self._gui_settings.encoder in {
                "gpu",
                "cpu",
                "auto",
            } else "gpu"
            self._env_ok_lines = validate_environment(EncoderBackend(enc))
        except ToolError as exc:
            messagebox.showerror("Smart Convert", str(exc))

        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._app_log_q: queue.Queue[str] = queue.Queue()
        self._ff_log_q: queue.Queue[tuple[str, bool]] = queue.Queue()
        self._progress_q: queue.Queue[tuple[float, float, str, str]] = queue.Queue()
        self._course_vars: list[tuple[tk.BooleanVar, Path]] = []
        self._job_total_videos = 0
        self._job_completed_videos = 0
        self._job_course_offsets: dict[str, int] = {}
        self._session_guard = WindowsSessionGuard()
        self._path_widgets: list[object] = []
        self._session_stats = SessionStats()

        self._font_ui = ctk.CTkFont(size=14)
        self._font_ui_bold = ctk.CTkFont(size=14, weight="bold")
        self._font_title = ctk.CTkFont(size=24, weight="bold")
        self._font_course = ctk.CTkFont(size=16)
        self._font_mono = ctk.CTkFont(family="Consolas", size=13)
        self._font_mono_sm = ctk.CTkFont(family="Consolas", size=12)

        self._build()
        self._apply_loaded_encode_settings()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_courses()
        self.after(80, self._drain_logs)
        self._app_log(f"Settings: {self._settings_path}")
        if removed:
            self._app_log(f"Cleaned {len(removed)} leftover conversion temp(s)")
        for line in self._env_ok_lines:
            self._app_log(f"env: {line}")

    def _apply_loaded_encode_settings(self) -> None:
        s = self._gui_settings
        profile = s.profile if s.profile in set(list_profile_names()) else "default"
        self.profile_var.set(profile)
        self.sample_var.set(s.sample_sec)
        self.min_savings_var.set(s.min_savings)
        self.cq_hevc_var.set(s.cq_hevc)
        self.cq_av1_var.set(s.cq_av1)
        self.preset_var.set(s.preset)
        self.codec_var.set(s.codec if s.codec in {"auto", "hevc", "av1"} else "auto")
        self.encoder_var.set(s.encoder if s.encoder in {"gpu", "cpu", "auto"} else "gpu")
        self.vmaf_var.set(s.vmaf if s.vmaf in {"off", "auto", "on"} else "auto")
        self.skip_same_codec_var.set(bool(s.skip_same_codec))
        self.overwrite_outbox_var.set(bool(s.overwrite_outbox))
        self.inbox_var.set(str(self.paths.inbox))
        self.outbox_var.set(str(self.paths.outbox))
        self.tmp_var.set(str(self.paths.tmp))

    def _seed_widgets_from_profile(self) -> None:
        """Apply NamedProfile defaults into widgets (CLI ``--profile`` parity)."""
        profile = get_profile(self.profile_var.get().strip() or "default")
        sample = profile.sample_seconds
        self.sample_var.set(
            str(int(sample)) if float(sample).is_integer() else str(sample)
        )
        self.min_savings_var.set(str(profile.min_savings))
        self.cq_hevc_var.set(str(profile.hevc_cq))
        self.cq_av1_var.set(str(profile.av1_cq))
        self.preset_var.set(profile.preset)
        self.encoder_var.set(
            profile.encoder if profile.encoder in {"gpu", "cpu", "auto"} else "gpu"
        )
        self.vmaf_var.set(profile.vmaf if profile.vmaf in {"off", "auto", "on"} else "auto")

    def _on_profile_changed(self) -> None:
        try:
            self._seed_widgets_from_profile()
        except ValueError as exc:
            messagebox.showerror("Smart Convert", str(exc))
            return
        self._app_log(f"Profile: {self.profile_var.get()}")

    def _collect_gui_settings(self) -> GuiSettings:
        return GuiSettings(
            inbox=self.inbox_var.get().strip(),
            outbox=self.outbox_var.get().strip(),
            tmp=self.tmp_var.get().strip(),
            profile=self.profile_var.get().strip() or "default",
            sample_sec=self.sample_var.get().strip(),
            min_savings=self.min_savings_var.get().strip(),
            cq_hevc=self.cq_hevc_var.get().strip(),
            cq_av1=self.cq_av1_var.get().strip(),
            preset=self.preset_var.get().strip(),
            codec=self.codec_var.get().strip(),
            encoder=self.encoder_var.get().strip(),
            skip_same_codec=bool(self.skip_same_codec_var.get()),
            overwrite_outbox=bool(self.overwrite_outbox_var.get()),
            vmaf=self.vmaf_var.get().strip(),
        )

    def _persist_settings(self) -> None:
        self._gui_settings = self._collect_gui_settings()
        save_gui_settings(self._gui_settings, self._settings_path)

    def _on_close(self) -> None:
        if self._worker and self._worker.is_alive():
            if not messagebox.askyesno(
                "Smart Convert",
                "A job is still running. Stop and exit?",
            ):
                return
            self._stop.set()
            killed = kill_active_subprocesses()
            if killed:
                self._app_log(f"Killed {killed} FFmpeg process tree(s)")
            self._session_guard.stop()
        else:
            self._session_guard.stop()
        try:
            self._persist_settings()
        except OSError:
            pass
        cleanup_conversion_temps(self.paths.tmp)
        self.destroy()

    def _build(self) -> None:
        build_ui(self)

    def _browse_inbox(self) -> None:
        browse_inbox(self)

    def _browse_outbox(self) -> None:
        browse_outbox(self)

    def _browse_tmp(self) -> None:
        browse_tmp(self)

    def _pick_courses_root(self) -> None:
        pick_courses_root(self)

    def _reset_paths_defaults(self) -> None:
        reset_paths_defaults(self)

    def _apply_paths(self) -> None:
        apply_paths(self)

    def _open_inbox(self) -> None:
        open_inbox(self)

    def _open_outbox(self) -> None:
        open_outbox(self)

    def refresh_courses(self) -> None:
        refresh_course_list(self)

    def _select_all(self) -> None:
        select_all_courses(self)

    def _select_none(self) -> None:
        select_none_courses(self)

    def _app_log(self, message: str) -> None:
        self._app_log_q.put(message)

    def _ff_log(self, message: str, *, replace_live: bool = True) -> None:
        self._ff_log_q.put((message, replace_live))

    def _textbox_line_count(self, widget: ctk.CTkTextbox) -> int:
        # end-1c is the last character; its line index is the line count.
        return int(float(widget.index("end-1c").split(".")[0]))

    def _trim_textbox(self, widget: ctk.CTkTextbox, max_lines: int) -> None:
        drop = trim_textbox_line_count(self._textbox_line_count(widget), max_lines)
        if drop <= 0:
            return
        widget.delete("1.0", f"{drop + 1}.0")

    def _drain_logs(self) -> None:
        app_inserted = False
        try:
            while True:
                message = self._app_log_q.get_nowait()
                self.app_log.insert("end", message + "\n")
                app_inserted = True
        except queue.Empty:
            pass
        if app_inserted:
            self._trim_textbox(self.app_log, APP_LOG_MAX_LINES)
            self.app_log.see("end")

        ff_inserted = False
        try:
            while True:
                message, replace_live = self._ff_log_q.get_nowait()
                if replace_live:
                    shown = message if len(message) < 140 else message[:137] + "..."
                    self.ff_live.configure(text=shown)
                    if "Lsize=" in message or ("speed=" in message and "frame=" in message):
                        key = (
                            message[message.find("time=") : message.find("time=") + 14]
                            if "time=" in message
                            else message
                        )
                        last = getattr(self, "_ff_last_hist", "")
                        if key != last:
                            self._ff_last_hist = key
                            self.ff_log.insert("end", message + "\n")
                            ff_inserted = True
                else:
                    self.ff_log.insert("end", message + "\n")
                    ff_inserted = True
        except queue.Empty:
            pass
        if ff_inserted:
            self._trim_textbox(self.ff_log, FF_LOG_MAX_LINES)
            self.ff_log.see("end")

        latest_progress: tuple[float, float, str, str] | None = None
        try:
            while True:
                latest_progress = self._progress_q.get_nowait()
        except queue.Empty:
            pass
        if latest_progress is not None:
            file_frac, job_frac, file_text, job_text = latest_progress
            self.file_bar.set(clamp01(file_frac))
            self.job_bar.set(clamp01(job_frac))
            self.file_progress_label.configure(text=file_text)
            self.job_progress_label.configure(text=job_text)

        self.after(80, self._drain_logs)

    def _emit_progress(self, update: ProgressUpdate) -> None:
        emit_progress(self, update)

    def start(self) -> None:
        start_job(self)

    def start_all(self) -> None:
        start_all_job(self)

    def stop(self) -> None:
        stop_job(self)

    def _set_running(self, running: bool) -> None:
        set_running(self, running)

    def _run(self, courses: list[Path]) -> None:
        run_job(self, courses)

    def _refresh_savings_labels(self) -> None:
        refresh_savings_labels(self)


def main() -> int:
    ensure_long_paths()
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
