from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .course import convert_course, iter_videos, list_course_dirs
from .models import AudioSettings, ConvertSettings, VideoCodec
from .paths import resolve_course_paths
from .probe import ToolError
from .progress import ProgressUpdate, clamp01
from .windows_guard import WindowsSessionGuard


# Utility app palette — muted graphite, not purple/glow
COLORS = {
    "bg": "#1a1d21",
    "panel": "#23282e",
    "panel2": "#2a3038",
    "border": "#3a424c",
    "text": "#e8eaed",
    "muted": "#9aa3ad",
    "accent": "#3d8bfd",
    "accent_hover": "#2f74d8",
    "danger": "#c23b3b",
    "danger_hover": "#a32f2f",
    "ok": "#3fa66b",
}


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Smart Convert NVENC")
        self.geometry("1100x760")
        self.minsize(920, 640)
        self.configure(fg_color=COLORS["bg"])

        self.paths = resolve_course_paths()
        self.paths.ensure()

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

        self._font_ui = ctk.CTkFont(size=14)
        self._font_ui_bold = ctk.CTkFont(size=14, weight="bold")
        self._font_title = ctk.CTkFont(size=24, weight="bold")
        self._font_course = ctk.CTkFont(size=16)
        self._font_mono = ctk.CTkFont(family="Consolas", size=13)
        self._font_mono_sm = ctk.CTkFont(family="Consolas", size=12)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.refresh_courses()
        self.after(80, self._drain_logs)

    def _on_close(self) -> None:
        if self._worker and self._worker.is_alive():
            if not messagebox.askyesno(
                "Smart Convert",
                "A job is still running. Stop and exit?",
            ):
                return
            self._stop.set()
            self._session_guard.stop()
        else:
            self._session_guard.stop()
        self.destroy()

    def _build(self) -> None:
        self.geometry("1200x820")
        self.minsize(1000, 700)

        root = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        root.pack(fill="both", expand=True, padx=14, pady=12)

        # --- Header (compact) ---
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            header,
            text="Smart Convert NVENC",
            font=self._font_title,
            text_color=COLORS["text"],
        ).pack(side="left")
        self.status = ctk.CTkLabel(
            header,
            text="Ready",
            font=self._font_ui_bold,
            text_color=COLORS["ok"],
        )
        self.status.pack(side="right")
        ctk.CTkLabel(
            root,
            text=f"inbox  {self.paths.inbox}    |    outbox  {self.paths.outbox}",
            font=self._font_mono_sm,
            text_color=COLORS["muted"],
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        # --- Top: courses + settings (fixed-ish height, does not steal log space) ---
        top = ctk.CTkFrame(root, fg_color="transparent", height=220)
        top.pack(fill="x", pady=(0, 8))
        top.pack_propagate(False)
        top.grid_columnconfigure(0, weight=3)
        top.grid_columnconfigure(1, weight=2)
        top.grid_rowconfigure(0, weight=1)

        courses_panel = ctk.CTkFrame(top, fg_color=COLORS["panel"], corner_radius=10)
        courses_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        courses_panel.grid_rowconfigure(1, weight=1)
        courses_panel.grid_columnconfigure(0, weight=1)

        courses_head = ctk.CTkFrame(courses_panel, fg_color="transparent")
        courses_head.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            courses_head,
            text="Courses in inbox",
            font=self._font_ui_bold,
            text_color=COLORS["text"],
        ).pack(side="left")
        self.course_count = ctk.CTkLabel(
            courses_head, text="", font=self._font_ui, text_color=COLORS["muted"]
        )
        self.course_count.pack(side="left", padx=(10, 0))

        self.course_list = ctk.CTkScrollableFrame(
            courses_panel, fg_color=COLORS["panel2"], corner_radius=8
        )
        self.course_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))

        course_btns = ctk.CTkFrame(courses_panel, fg_color="transparent")
        course_btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        for text, cmd in (
            ("Refresh", self.refresh_courses),
            ("Select all", self._select_all),
            ("Clear", self._select_none),
        ):
            ctk.CTkButton(
                course_btns,
                text=text,
                width=100,
                height=30,
                font=self._font_ui,
                fg_color=COLORS["panel2"],
                hover_color=COLORS["border"],
                command=cmd,
            ).pack(side="left", padx=(0, 6))

        settings_panel = ctk.CTkFrame(top, fg_color=COLORS["panel"], corner_radius=10)
        settings_panel.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            settings_panel,
            text="Settings",
            font=self._font_ui_bold,
            text_color=COLORS["text"],
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.sample_var = tk.StringVar(value="20")
        self.min_savings_var = tk.StringVar(value="0.10")
        self.cq_hevc_var = tk.StringVar(value="28")
        self.cq_av1_var = tk.StringVar(value="32")
        self.preset_var = tk.StringVar(value="p6")
        self.codec_var = tk.StringVar(value="auto")

        fields = ctk.CTkFrame(settings_panel, fg_color="transparent")
        fields.pack(fill="x", padx=4)
        self._row(fields, "Sample sec", self.sample_var)
        self._row(fields, "Min savings", self.min_savings_var)
        self._row(fields, "CQ HEVC", self.cq_hevc_var)
        self._row(fields, "CQ AV1", self.cq_av1_var)
        self._row(fields, "Preset", self.preset_var)

        codec_row = ctk.CTkFrame(fields, fg_color="transparent")
        codec_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(
            codec_row,
            text="Codec",
            width=100,
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        ).pack(side="left")
        ctk.CTkOptionMenu(
            codec_row,
            variable=self.codec_var,
            values=["auto", "hevc", "av1"],
            width=120,
            height=28,
            font=self._font_ui,
            fg_color=COLORS["panel2"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["accent"],
        ).pack(side="left")

        action = ctk.CTkFrame(settings_panel, fg_color="transparent")
        action.pack(fill="x", padx=12, pady=(6, 10), side="bottom")
        self.start_btn = ctk.CTkButton(
            action,
            text="Start selected",
            height=32,
            font=self._font_ui_bold,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self.start,
        )
        self.start_btn.pack(fill="x", pady=(0, 4))
        self.start_all_btn = ctk.CTkButton(
            action,
            text="Start all",
            height=30,
            font=self._font_ui,
            fg_color=COLORS["panel2"],
            hover_color=COLORS["border"],
            command=self.start_all,
        )
        self.start_all_btn.pack(fill="x", pady=(0, 4))
        self.stop_btn = ctk.CTkButton(
            action,
            text="Stop after current video",
            height=30,
            font=self._font_ui,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            state="disabled",
            command=self.stop,
        )
        self.stop_btn.pack(fill="x")

        # --- Progress (compact) ---
        progress_box = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=10)
        progress_box.pack(fill="x", pady=(0, 8))

        self.file_progress_label = ctk.CTkLabel(
            progress_box,
            text="File: —",
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        )
        self.file_progress_label.pack(fill="x", padx=12, pady=(8, 2))
        self.file_bar = ctk.CTkProgressBar(
            progress_box,
            height=14,
            progress_color=COLORS["accent"],
            fg_color=COLORS["panel2"],
        )
        self.file_bar.pack(fill="x", padx=12, pady=(0, 6))
        self.file_bar.set(0)

        self.job_progress_label = ctk.CTkLabel(
            progress_box,
            text="Job: —",
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        )
        self.job_progress_label.pack(fill="x", padx=12, pady=(0, 2))
        self.job_bar = ctk.CTkProgressBar(
            progress_box,
            height=14,
            progress_color=COLORS["ok"],
            fg_color=COLORS["panel2"],
        )
        self.job_bar.pack(fill="x", padx=12, pady=(0, 8))
        self.job_bar.set(0)

        # --- Logs take ALL remaining vertical space ---
        logs = ctk.CTkFrame(root, fg_color="transparent")
        logs.pack(fill="both", expand=True)
        logs.grid_columnconfigure(0, weight=1)
        logs.grid_columnconfigure(1, weight=1)
        logs.grid_rowconfigure(0, weight=1)

        app_box = ctk.CTkFrame(logs, fg_color=COLORS["panel"], corner_radius=10)
        app_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        app_box.grid_rowconfigure(1, weight=1)
        app_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            app_box,
            text="App log",
            font=self._font_ui_bold,
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.app_log = ctk.CTkTextbox(
            app_box,
            font=self._font_mono,
            fg_color=COLORS["panel2"],
            text_color=COLORS["text"],
            wrap="word",
        )
        self.app_log.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        ff_box = ctk.CTkFrame(logs, fg_color=COLORS["panel"], corner_radius=10)
        ff_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ff_box.grid_rowconfigure(2, weight=1)
        ff_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            ff_box,
            text="FFmpeg",
            font=self._font_ui_bold,
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.ff_live = ctk.CTkLabel(
            ff_box,
            text="idle",
            anchor="w",
            font=self._font_mono_sm,
            text_color=COLORS["accent"],
        )
        self.ff_live.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 2))
        self.ff_log = ctk.CTkTextbox(
            ff_box,
            font=self._font_mono_sm,
            fg_color=COLORS["panel2"],
            text_color=COLORS["muted"],
            wrap="none",
        )
        self.ff_log.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _row(self, parent: ctk.CTkFrame, label: str, var: tk.StringVar) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(
            row,
            text=label,
            width=100,
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        ).pack(side="left")
        ctk.CTkEntry(
            row,
            textvariable=var,
            width=120,
            height=28,
            font=self._font_ui,
            fg_color=COLORS["panel2"],
            border_color=COLORS["border"],
        ).pack(side="left")

    def refresh_courses(self) -> None:
        for child in self.course_list.winfo_children():
            child.destroy()
        self._course_vars.clear()
        courses = list_course_dirs(self.paths.inbox)
        self.course_count.configure(text=f"{len(courses)} found")
        if not courses:
            ctk.CTkLabel(
                self.course_list,
                text="Inbox is empty — drop course folders into courses/inbox",
                font=self._font_ui,
                text_color=COLORS["muted"],
            ).pack(anchor="w", padx=8, pady=12)
            return
        for course in courses:
            var = tk.BooleanVar(value=False)
            row = ctk.CTkFrame(self.course_list, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=4)
            ctk.CTkCheckBox(
                row,
                text=course.name,
                variable=var,
                font=self._font_course,
                text_color=COLORS["text"],
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                border_color=COLORS["border"],
                checkmark_color="#ffffff",
            ).pack(anchor="w", fill="x")
            self._course_vars.append((var, course))
        self._app_log(f"Found {len(courses)} course(s) in inbox")

    def _select_all(self) -> None:
        for var, _ in self._course_vars:
            var.set(True)

    def _select_none(self) -> None:
        for var, _ in self._course_vars:
            var.set(False)

    def _app_log(self, message: str) -> None:
        self._app_log_q.put(message)

    def _ff_log(self, message: str, *, replace_live: bool = True) -> None:
        self._ff_log_q.put((message, replace_live))

    def _drain_logs(self) -> None:
        try:
            while True:
                message = self._app_log_q.get_nowait()
                self.app_log.insert("end", message + "\n")
                self.app_log.see("end")
        except queue.Empty:
            pass

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
                            self.ff_log.see("end")
                else:
                    self.ff_log.insert("end", message + "\n")
                    self.ff_log.see("end")
        except queue.Empty:
            pass

        try:
            while True:
                file_frac, job_frac, file_text, job_text = self._progress_q.get_nowait()
                self.file_bar.set(clamp01(file_frac))
                self.job_bar.set(clamp01(job_frac))
                self.file_progress_label.configure(text=file_text)
                self.job_progress_label.configure(text=job_text)
        except queue.Empty:
            pass

        self.after(80, self._drain_logs)

    def _emit_progress(self, update: ProgressUpdate) -> None:
        offset = self._job_course_offsets.get(update.course_name, 0)
        done_before = offset + (update.video_index - 1)
        overall_units = done_before + update.file_fraction
        total = max(1, self._job_total_videos)
        job_frac = overall_units / total
        phase = update.phase.replace("_", " ")
        file_text = (
            f"File: {update.video_name}  ({update.video_index}/{update.videos_in_course})  "
            f"{phase}  {update.file_fraction * 100:.0f}%"
        )
        job_text = (
            f"Job: {int(overall_units)}/{total} videos  ({job_frac * 100:.0f}%)  "
            f"course: {update.course_name}"
        )
        self._progress_q.put((update.file_fraction, job_frac, file_text, job_text))

    def _settings(self) -> ConvertSettings:
        codec_raw = self.codec_var.get()
        force = None if codec_raw == "auto" else VideoCodec(codec_raw)
        return ConvertSettings(
            sample_seconds=float(self.sample_var.get()),
            min_savings=float(self.min_savings_var.get()),
            hevc_cq=int(self.cq_hevc_var.get()),
            av1_cq=int(self.cq_av1_var.get()),
            preset=self.preset_var.get().strip(),
            audio=AudioSettings.parse("copy"),
            force_codec=force,
        )

    def _selected_courses(self) -> list[Path]:
        return [path for var, path in self._course_vars if var.get()]

    def start(self) -> None:
        courses = self._selected_courses()
        if not courses:
            messagebox.showwarning("Smart Convert", "Select at least one course.")
            return
        self._run(courses)

    def start_all(self) -> None:
        self.refresh_courses()
        courses = [path for _, path in self._course_vars]
        if not courses:
            messagebox.showwarning("Smart Convert", "Inbox is empty.")
            return
        self._select_all()
        self._run(courses)

    def stop(self) -> None:
        self._stop.set()
        self._app_log("Stop requested (after current video)...")
        self.status.configure(text="Stopping...", text_color="#e0a84c")

    def _set_running(self, running: bool) -> None:
        state_idle = "normal" if not running else "disabled"
        state_run = "normal" if running else "disabled"
        self.start_btn.configure(state=state_idle)
        self.start_all_btn.configure(state=state_idle)
        self.stop_btn.configure(state=state_run)

    def _run(self, courses: list[Path]) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Smart Convert", "Already running.")
            return

        try:
            settings = self._settings()
        except ValueError as exc:
            messagebox.showerror("Smart Convert", f"Bad settings: {exc}")
            return

        self._stop.clear()
        self._set_running(True)
        self._job_total_videos = sum(len(iter_videos(c)) for c in courses)
        self._job_completed_videos = 0
        self._job_course_offsets = {}
        offset = 0
        for course in courses:
            self._job_course_offsets[course.name] = offset
            offset += len(iter_videos(course))

        self.file_bar.set(0)
        self.job_bar.set(0)
        self.file_progress_label.configure(text="File: starting...")
        self.job_progress_label.configure(
            text=f"Job: 0/{self._job_total_videos} videos (0%)"
        )
        self.status.configure(text=f"Running 0/{len(courses)}...", text_color=COLORS["accent"])
        self.ff_live.configure(text="starting...")
        self._app_log("=" * 60)
        self._app_log(
            f"Queue: {len(courses)} course(s), {self._job_total_videos} videos, sequential"
        )
        try:
            hwnd = int(self.winfo_id())
        except tk.TclError:
            hwnd = None
        self._session_guard.start(hwnd)
        self._app_log(
            "Windows guard ON: sleep blocked, pending reboot/shutdown aborted while job runs"
        )

        def worker() -> None:
            try:
                for i, course in enumerate(courses, start=1):
                    if self._stop.is_set():
                        self._app_log("Stopped by user.")
                        break
                    self.after(
                        0,
                        lambda i=i, n=len(courses), name=course.name: self.status.configure(
                            text=f"Running {i}/{n}: {name}",
                            text_color=COLORS["accent"],
                        ),
                    )
                    self._ff_log(f"--- course: {course.name} ---", replace_live=False)

                    try:
                        convert_course(
                            course,
                            self.paths,
                            settings,
                            race_once=True,
                            log=self._app_log,
                            on_ffmpeg_progress=lambda line: self._ff_log(line, replace_live=True),
                            on_progress=self._emit_progress,
                            should_stop=self._stop.is_set,
                        )
                    except RuntimeError as exc:
                        if "Stopped by user" in str(exc):
                            self._app_log("Stopped by user.")
                            break
                        raise
                else:
                    self._app_log("All queued courses finished.")
                    self._progress_q.put(
                        (
                            1.0,
                            1.0,
                            "File: done",
                            f"Job: {self._job_total_videos}/{self._job_total_videos} videos (100%)",
                        )
                    )
            except (
                ToolError,
                FileNotFoundError,
                FileExistsError,
                ValueError,
                OSError,
                RuntimeError,
            ) as exc:
                self._app_log(f"ERROR: {exc}")
                self.after(0, lambda: messagebox.showerror("Smart Convert", str(exc)))
            finally:
                self.after(0, self._session_guard.stop)
                self.after(
                    0,
                    lambda: self._app_log("Windows guard OFF"),
                )
                self.after(0, lambda: self._set_running(False))
                self.after(0, self.refresh_courses)
                self.after(
                    0,
                    lambda: self.status.configure(text="Ready", text_color=COLORS["ok"]),
                )
                self.after(0, lambda: self.ff_live.configure(text="idle"))

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
