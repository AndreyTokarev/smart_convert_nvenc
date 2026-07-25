from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __version__
from .course import convert_course, iter_videos, list_course_dirs, tree_size
from .ffmpeg_runner import FFmpegCancelled, kill_active_subprocesses
from .gui_settings import GuiSettings, default_settings_path, load_gui_settings, save_gui_settings
from .models import AudioSettings, ConvertSettings, EncoderBackend, VideoCodec, VmafMode
from .paths import CoursePaths, resolve_course_paths
from .probe import ToolError, validate_environment
from .progress import ProgressUpdate, clamp01, trim_textbox_line_count
from .session import SessionStats, format_gib_or_mib
from .temp_paths import cleanup_conversion_temps
from .windows_guard import WindowsSessionGuard


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

APP_LOG_MAX_LINES = 2000
FF_LOG_MAX_LINES = 1000


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


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

    def _collect_gui_settings(self) -> GuiSettings:
        return GuiSettings(
            inbox=self.inbox_var.get().strip(),
            outbox=self.outbox_var.get().strip(),
            tmp=self.tmp_var.get().strip(),
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
        root = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        root.pack(fill="both", expand=True, padx=14, pady=12)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            header,
            text=f"Smart Convert NVENC  v{__version__}",
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

        paths_panel = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=10)
        paths_panel.pack(fill="x", pady=(0, 8))
        paths_head = ctk.CTkFrame(paths_panel, fg_color="transparent")
        paths_head.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(
            paths_head,
            text="Folders",
            font=self._font_ui_bold,
            text_color=COLORS["text"],
        ).pack(side="left")
        path_btns = ctk.CTkFrame(paths_head, fg_color="transparent")
        path_btns.pack(side="right")
        for text, cmd in (
            ("Courses root…", self._pick_courses_root),
            ("Apply", self._apply_paths),
            ("Defaults", self._reset_paths_defaults),
        ):
            btn = ctk.CTkButton(
                path_btns,
                text=text,
                width=110,
                height=28,
                font=self._font_ui,
                fg_color=COLORS["panel2"],
                hover_color=COLORS["border"],
                command=cmd,
            )
            btn.pack(side="left", padx=(6, 0))
            self._path_widgets.append(btn)

        self.inbox_var = tk.StringVar()
        self.outbox_var = tk.StringVar()
        self.tmp_var = tk.StringVar()
        self._path_row(paths_panel, "inbox", self.inbox_var, self._browse_inbox)
        self._path_row(paths_panel, "outbox", self.outbox_var, self._browse_outbox)
        self._path_row(paths_panel, "tmp", self.tmp_var, self._browse_tmp)

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
            ("Open inbox", self._open_inbox),
            ("Open outbox", self._open_outbox),
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
        self.encoder_var = tk.StringVar(value="gpu")
        self.vmaf_var = tk.StringVar(value="auto")
        self.skip_same_codec_var = tk.BooleanVar(value=True)
        self.overwrite_outbox_var = tk.BooleanVar(value=True)

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

        enc_row = ctk.CTkFrame(fields, fg_color="transparent")
        enc_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(
            enc_row,
            text="Encoder",
            width=100,
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        ).pack(side="left")
        ctk.CTkOptionMenu(
            enc_row,
            variable=self.encoder_var,
            values=["gpu", "cpu", "auto"],
            width=120,
            height=28,
            font=self._font_ui,
            fg_color=COLORS["panel2"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["accent"],
        ).pack(side="left")

        vmaf_row = ctk.CTkFrame(fields, fg_color="transparent")
        vmaf_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(
            vmaf_row,
            text="VMAF",
            width=100,
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        ).pack(side="left")
        ctk.CTkOptionMenu(
            vmaf_row,
            variable=self.vmaf_var,
            values=["auto", "off", "on"],
            width=120,
            height=28,
            font=self._font_ui,
            fg_color=COLORS["panel2"],
            button_color=COLORS["border"],
            button_hover_color=COLORS["accent"],
        ).pack(side="left")

        skip_row = ctk.CTkFrame(fields, fg_color="transparent")
        skip_row.pack(fill="x", padx=10, pady=(4, 2))
        ctk.CTkCheckBox(
            skip_row,
            text="Skip if already HEVC/AV1",
            variable=self.skip_same_codec_var,
            font=self._font_ui,
            text_color=COLORS["text"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#ffffff",
        ).pack(anchor="w")
        ctk.CTkCheckBox(
            skip_row,
            text="Overwrite existing outbox course",
            variable=self.overwrite_outbox_var,
            font=self._font_ui,
            text_color=COLORS["text"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#ffffff",
        ).pack(anchor="w", pady=(4, 0))

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
            text="Stop",
            height=30,
            font=self._font_ui,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            state="disabled",
            command=self.stop,
        )
        self.stop_btn.pack(fill="x")

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
        self.job_bar.pack(fill="x", padx=12, pady=(0, 6))
        self.job_bar.set(0)

        savings = ctk.CTkFrame(progress_box, fg_color="transparent")
        savings.pack(fill="x", padx=12, pady=(0, 10))
        savings.grid_columnconfigure(0, weight=1)
        savings.grid_columnconfigure(1, weight=1)
        savings.grid_columnconfigure(2, weight=1)

        self.last_course_label = ctk.CTkLabel(
            savings,
            text="Last course: —",
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["text"],
        )
        self.last_course_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.session_freed_label = ctk.CTkLabel(
            savings,
            text="Session freed: 0 MiB",
            anchor="w",
            font=self._font_ui_bold,
            text_color=COLORS["ok"],
        )
        self.session_freed_label.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.session_rate_label = ctk.CTkLabel(
            savings,
            text="0%",
            anchor="e",
            font=self._font_ui,
            text_color=COLORS["muted"],
        )
        self.session_rate_label.grid(row=0, column=2, sticky="ew")

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

    def _path_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        var: tk.StringVar,
        browse_cmd: object,
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(
            row,
            text=label,
            width=56,
            anchor="w",
            font=self._font_ui,
            text_color=COLORS["muted"],
        ).pack(side="left")
        entry = ctk.CTkEntry(
            row,
            textvariable=var,
            height=28,
            font=self._font_mono_sm,
            fg_color=COLORS["panel2"],
            border_color=COLORS["border"],
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        btn = ctk.CTkButton(
            row,
            text="Browse…",
            width=88,
            height=28,
            font=self._font_ui,
            fg_color=COLORS["panel2"],
            hover_color=COLORS["border"],
            command=browse_cmd,
        )
        btn.pack(side="left")
        self._path_widgets.extend([entry, btn])

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

    def _busy(self) -> bool:
        return bool(self._worker and self._worker.is_alive())

    def _browse_folder(self, title: str, current: str) -> Path | None:
        initial = current if Path(current).is_dir() else str(Path.home())
        chosen = filedialog.askdirectory(title=title, initialdir=initial, mustexist=True)
        if not chosen:
            return None
        return Path(chosen)

    def _browse_inbox(self) -> None:
        path = self._browse_folder("Select inbox folder", self.inbox_var.get())
        if path:
            self.inbox_var.set(str(path.resolve()))

    def _browse_outbox(self) -> None:
        path = self._browse_folder("Select outbox folder", self.outbox_var.get())
        if path:
            self.outbox_var.set(str(path.resolve()))

    def _browse_tmp(self) -> None:
        path = self._browse_folder("Select tmp folder", self.tmp_var.get())
        if path:
            self.tmp_var.set(str(path.resolve()))

    def _pick_courses_root(self) -> None:
        if self._busy():
            messagebox.showwarning("Smart Convert", "Stop the job before changing folders.")
            return
        path = self._browse_folder(
            "Select courses root (inbox/outbox/tmp inside)",
            self.inbox_var.get(),
        )
        if not path:
            return
        resolved = resolve_course_paths(courses_root=path)
        self.inbox_var.set(str(resolved.inbox))
        self.outbox_var.set(str(resolved.outbox))
        self.tmp_var.set(str(resolved.tmp))
        self._apply_paths()

    def _reset_paths_defaults(self) -> None:
        if self._busy():
            messagebox.showwarning("Smart Convert", "Stop the job before changing folders.")
            return
        defaults = resolve_course_paths()
        self.inbox_var.set(str(defaults.inbox))
        self.outbox_var.set(str(defaults.outbox))
        self.tmp_var.set(str(defaults.tmp))
        self._apply_paths()

    def _apply_paths(self) -> None:
        if self._busy():
            messagebox.showwarning("Smart Convert", "Stop the job before changing folders.")
            return
        inbox = self.inbox_var.get().strip()
        outbox = self.outbox_var.get().strip()
        tmp = self.tmp_var.get().strip()
        if not inbox or not outbox or not tmp:
            messagebox.showerror("Smart Convert", "inbox, outbox and tmp must all be set.")
            return
        new_paths = CoursePaths(
            inbox=Path(inbox).expanduser().resolve(),
            outbox=Path(outbox).expanduser().resolve(),
            tmp=Path(tmp).expanduser().resolve(),
        )
        try:
            new_paths.ensure()
        except OSError as exc:
            messagebox.showerror("Smart Convert", f"Cannot create folders: {exc}")
            return
        self.paths = new_paths
        self.inbox_var.set(str(new_paths.inbox))
        self.outbox_var.set(str(new_paths.outbox))
        self.tmp_var.set(str(new_paths.tmp))
        try:
            self._persist_settings()
        except OSError as exc:
            messagebox.showerror("Smart Convert", f"Cannot save settings: {exc}")
            return
        cleanup_conversion_temps(self.paths.tmp)
        self._app_log(f"Paths applied. inbox={self.paths.inbox}")
        self.refresh_courses()

    def _open_in_explorer(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except OSError as exc:
            messagebox.showerror("Smart Convert", str(exc))

    def _open_inbox(self) -> None:
        self._open_in_explorer(self.paths.inbox)

    def _open_outbox(self) -> None:
        self._open_in_explorer(self.paths.outbox)

    def refresh_courses(self) -> None:
        for child in self.course_list.winfo_children():
            child.destroy()
        self._course_vars.clear()
        courses = list_course_dirs(self.paths.inbox, by_size=True)
        self.course_count.configure(text=f"{len(courses)} found")
        if not courses:
            ctk.CTkLabel(
                self.course_list,
                text="Inbox is empty — drop course folders into the inbox path",
                font=self._font_ui,
                text_color=COLORS["muted"],
            ).pack(anchor="w", padx=8, pady=12)
            return
        for course in courses:
            size_mib = tree_size(course) / (1024 * 1024)
            var = tk.BooleanVar(value=False)
            row = ctk.CTkFrame(self.course_list, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=4)
            ctk.CTkCheckBox(
                row,
                text=f"{course.name}  ({size_mib:.0f} MiB)",
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
        offset = self._job_course_offsets.get(update.course_name, 0)
        done_before = offset + (update.video_index - 1)
        overall_units = done_before + update.file_fraction
        total = max(1, self._job_total_videos)
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
        self._progress_q.put((update.file_fraction, job_frac, file_text, job_text))

    def _settings(self) -> ConvertSettings:
        codec_raw = self.codec_var.get()
        force = None if codec_raw == "auto" else VideoCodec(codec_raw)
        enc_raw = self.encoder_var.get().strip().lower()
        if enc_raw not in {"gpu", "cpu", "auto"}:
            enc_raw = "gpu"
        vmaf_raw = self.vmaf_var.get().strip().lower()
        if vmaf_raw not in {"off", "auto", "on"}:
            vmaf_raw = "auto"
        return ConvertSettings(
            sample_seconds=float(self.sample_var.get()),
            min_savings=float(self.min_savings_var.get()),
            hevc_cq=int(self.cq_hevc_var.get()),
            av1_cq=int(self.cq_av1_var.get()),
            preset=self.preset_var.get().strip(),
            audio=AudioSettings.parse("copy"),
            force_codec=force,
            skip_same_codec=bool(self.skip_same_codec_var.get()),
            encoder=EncoderBackend(enc_raw),
            vmaf=VmafMode(vmaf_raw),
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
        killed = kill_active_subprocesses()
        if killed:
            self._app_log(f"Stop: killed {killed} FFmpeg process tree(s)")
        else:
            self._app_log("Stop requested...")
        self.status.configure(text="Stopping...", text_color="#e0a84c")

    def _set_running(self, running: bool) -> None:
        state_idle = "normal" if not running else "disabled"
        state_run = "normal" if running else "disabled"
        self.start_btn.configure(state=state_idle)
        self.start_all_btn.configure(state=state_idle)
        self.stop_btn.configure(state=state_run)
        for widget in self._path_widgets:
            try:
                widget.configure(state=state_idle)
            except tk.TclError:
                pass

    def _run(self, courses: list[Path]) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Smart Convert", "Already running.")
            return
        courses = sorted(courses, key=lambda p: (-tree_size(p), p.name.lower()))

        try:
            settings = self._settings()
            self._persist_settings()
        except ValueError as exc:
            messagebox.showerror("Smart Convert", f"Bad settings: {exc}")
            return
        except OSError as exc:
            messagebox.showerror("Smart Convert", f"Cannot save settings: {exc}")
            return

        self._stop.clear()
        self._set_running(True)
        self._session_stats = SessionStats()
        self._refresh_savings_labels()
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
                        result = convert_course(
                            course,
                            self.paths,
                            settings,
                            race_once=True,
                            overwrite_outbox=bool(self.overwrite_outbox_var.get()),
                            log=self._app_log,
                            on_ffmpeg_progress=lambda line: self._ff_log(line, replace_live=True),
                            on_progress=self._emit_progress,
                            should_stop=self._stop.is_set,
                        )
                        item = self._session_stats.add_course(
                            result.name,
                            result.original_size,
                            result.final_size,
                        )
                        self._app_log(
                            f"Course result: {result.name}: "
                            f"{format_gib_or_mib(result.original_size)} → "
                            f"{format_gib_or_mib(result.final_size)} "
                            f"(freed {format_gib_or_mib(item.freed_bytes)}, "
                            f"{item.ratio * 100:.1f}%)"
                        )
                        self.after(0, self._refresh_savings_labels)
                    except FFmpegCancelled:
                        self._app_log("Stopped by user.")
                        break
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
                if self._session_stats.courses:
                    self._app_log(self._session_stats.summary_line())
                    self.after(0, self._refresh_savings_labels)
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
                    self._app_log("Stopped by user.")
                else:
                    err_text = str(exc)
                    self._app_log(f"ERROR: {err_text}")
                    self.after(
                        0,
                        lambda msg=err_text: messagebox.showerror("Smart Convert", msg),
                    )
            finally:
                cleanup_conversion_temps(self.paths.tmp)
                self.after(0, self._session_guard.stop)
                self.after(0, lambda: self._app_log("Windows guard OFF"))
                self.after(0, lambda: self._set_running(False))
                self.after(0, self.refresh_courses)
                self.after(
                    0,
                    lambda: self.status.configure(text="Ready", text_color=COLORS["ok"]),
                )
                self.after(0, lambda: self.ff_live.configure(text="idle"))

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _refresh_savings_labels(self) -> None:
        stats = self._session_stats
        last = stats.last_course()
        if last is None:
            self.last_course_label.configure(text="Last course: —")
        else:
            self.last_course_label.configure(
                text=(
                    f"Last: {format_gib_or_mib(last.freed_bytes)} freed "
                    f"({last.ratio * 100:.1f}%)"
                )
            )
        self.session_freed_label.configure(
            text=f"Session freed: {format_gib_or_mib(stats.freed_bytes)}"
        )
        if stats.courses:
            self.session_rate_label.configure(
                text=f"{stats.ratio * 100:.1f}% · {stats.mib_per_hour:.0f} MiB/h"
            )
        else:
            self.session_rate_label.configure(text="—")


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
