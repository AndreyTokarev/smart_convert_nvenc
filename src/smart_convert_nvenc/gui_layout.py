from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk
import tkinter as tk

from . import __version__
from .gui_theme import COLORS
from .profiles import list_profile_names

if TYPE_CHECKING:
    from .gui import App


def build_ui(app: App) -> None:
    root = ctk.CTkFrame(app, fg_color=COLORS["bg"])
    root.pack(fill="both", expand=True, padx=14, pady=12)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        header,
        text=f"Smart Convert NVENC  v{__version__}",
        font=app._font_title,
        text_color=COLORS["text"],
    ).pack(side="left")
    app.status = ctk.CTkLabel(
        header,
        text="Ready",
        font=app._font_ui_bold,
        text_color=COLORS["ok"],
    )
    app.status.pack(side="right")

    paths_panel = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=10)
    paths_panel.pack(fill="x", pady=(0, 8))
    paths_head = ctk.CTkFrame(paths_panel, fg_color="transparent")
    paths_head.pack(fill="x", padx=12, pady=(8, 4))
    ctk.CTkLabel(
        paths_head,
        text="Folders",
        font=app._font_ui_bold,
        text_color=COLORS["text"],
    ).pack(side="left")
    path_btns = ctk.CTkFrame(paths_head, fg_color="transparent")
    path_btns.pack(side="right")
    for text, cmd in (
        ("Courses root…", app._pick_courses_root),
        ("Apply", app._apply_paths),
        ("Defaults", app._reset_paths_defaults),
    ):
        btn = ctk.CTkButton(
            path_btns,
            text=text,
            width=110,
            height=28,
            font=app._font_ui,
            fg_color=COLORS["panel2"],
            hover_color=COLORS["border"],
            command=cmd,
        )
        btn.pack(side="left", padx=(6, 0))
        app._path_widgets.append(btn)

    app.inbox_var = tk.StringVar()
    app.outbox_var = tk.StringVar()
    app.tmp_var = tk.StringVar()
    path_row(app, paths_panel, "inbox", app.inbox_var, app._browse_inbox)
    path_row(app, paths_panel, "outbox", app.outbox_var, app._browse_outbox)
    path_row(app, paths_panel, "tmp", app.tmp_var, app._browse_tmp)

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
        font=app._font_ui_bold,
        text_color=COLORS["text"],
    ).pack(side="left")
    app.course_count = ctk.CTkLabel(
        courses_head, text="", font=app._font_ui, text_color=COLORS["muted"]
    )
    app.course_count.pack(side="left", padx=(10, 0))

    app.course_list = ctk.CTkScrollableFrame(
        courses_panel, fg_color=COLORS["panel2"], corner_radius=8
    )
    app.course_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))

    course_btns = ctk.CTkFrame(courses_panel, fg_color="transparent")
    course_btns.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
    for text, cmd in (
        ("Refresh", app.refresh_courses),
        ("Select all", app._select_all),
        ("Clear", app._select_none),
        ("Open inbox", app._open_inbox),
        ("Open outbox", app._open_outbox),
    ):
        ctk.CTkButton(
            course_btns,
            text=text,
            width=100,
            height=30,
            font=app._font_ui,
            fg_color=COLORS["panel2"],
            hover_color=COLORS["border"],
            command=cmd,
        ).pack(side="left", padx=(0, 6))

    settings_panel = ctk.CTkFrame(top, fg_color=COLORS["panel"], corner_radius=10)
    settings_panel.grid(row=0, column=1, sticky="nsew")

    ctk.CTkLabel(
        settings_panel,
        text="Settings",
        font=app._font_ui_bold,
        text_color=COLORS["text"],
    ).pack(anchor="w", padx=12, pady=(10, 4))

    app.profile_var = tk.StringVar(value="default")
    app.sample_var = tk.StringVar(value="20")
    app.min_savings_var = tk.StringVar(value="0.10")
    app.cq_hevc_var = tk.StringVar(value="28")
    app.cq_av1_var = tk.StringVar(value="32")
    app.preset_var = tk.StringVar(value="p6")
    app.codec_var = tk.StringVar(value="auto")
    app.encoder_var = tk.StringVar(value="gpu")
    app.vmaf_var = tk.StringVar(value="auto")
    app.skip_same_codec_var = tk.BooleanVar(value=True)
    app.overwrite_outbox_var = tk.BooleanVar(value=True)

    fields = ctk.CTkFrame(settings_panel, fg_color="transparent")
    fields.pack(fill="x", padx=4)

    profile_row = ctk.CTkFrame(fields, fg_color="transparent")
    profile_row.pack(fill="x", padx=10, pady=2)
    ctk.CTkLabel(
        profile_row,
        text="Profile",
        width=100,
        anchor="w",
        font=app._font_ui,
        text_color=COLORS["muted"],
    ).pack(side="left")
    ctk.CTkOptionMenu(
        profile_row,
        variable=app.profile_var,
        values=list_profile_names(),
        width=120,
        height=28,
        font=app._font_ui,
        fg_color=COLORS["panel2"],
        button_color=COLORS["border"],
        button_hover_color=COLORS["accent"],
        command=lambda _value: app._on_profile_changed(),
    ).pack(side="left")

    settings_row(app, fields, "Sample sec", app.sample_var)
    settings_row(app, fields, "Min savings", app.min_savings_var)
    settings_row(app, fields, "CQ HEVC", app.cq_hevc_var)
    settings_row(app, fields, "CQ AV1", app.cq_av1_var)
    settings_row(app, fields, "Preset", app.preset_var)

    codec_row = ctk.CTkFrame(fields, fg_color="transparent")
    codec_row.pack(fill="x", padx=10, pady=2)
    ctk.CTkLabel(
        codec_row,
        text="Codec",
        width=100,
        anchor="w",
        font=app._font_ui,
        text_color=COLORS["muted"],
    ).pack(side="left")
    ctk.CTkOptionMenu(
        codec_row,
        variable=app.codec_var,
        values=["auto", "hevc", "av1"],
        width=120,
        height=28,
        font=app._font_ui,
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
        font=app._font_ui,
        text_color=COLORS["muted"],
    ).pack(side="left")
    ctk.CTkOptionMenu(
        enc_row,
        variable=app.encoder_var,
        values=["gpu", "cpu", "auto"],
        width=120,
        height=28,
        font=app._font_ui,
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
        font=app._font_ui,
        text_color=COLORS["muted"],
    ).pack(side="left")
    ctk.CTkOptionMenu(
        vmaf_row,
        variable=app.vmaf_var,
        values=["auto", "off", "on"],
        width=120,
        height=28,
        font=app._font_ui,
        fg_color=COLORS["panel2"],
        button_color=COLORS["border"],
        button_hover_color=COLORS["accent"],
    ).pack(side="left")

    skip_row = ctk.CTkFrame(fields, fg_color="transparent")
    skip_row.pack(fill="x", padx=10, pady=(4, 2))
    ctk.CTkCheckBox(
        skip_row,
        text="Skip if already HEVC/AV1",
        variable=app.skip_same_codec_var,
        font=app._font_ui,
        text_color=COLORS["text"],
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        border_color=COLORS["border"],
        checkmark_color="#ffffff",
    ).pack(anchor="w")
    ctk.CTkCheckBox(
        skip_row,
        text="Overwrite existing outbox course",
        variable=app.overwrite_outbox_var,
        font=app._font_ui,
        text_color=COLORS["text"],
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        border_color=COLORS["border"],
        checkmark_color="#ffffff",
    ).pack(anchor="w", pady=(4, 0))

    action = ctk.CTkFrame(settings_panel, fg_color="transparent")
    action.pack(fill="x", padx=12, pady=(6, 10), side="bottom")
    app.start_btn = ctk.CTkButton(
        action,
        text="Start selected",
        height=32,
        font=app._font_ui_bold,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        command=app.start,
    )
    app.start_btn.pack(fill="x", pady=(0, 4))
    app.start_all_btn = ctk.CTkButton(
        action,
        text="Start all",
        height=30,
        font=app._font_ui,
        fg_color=COLORS["panel2"],
        hover_color=COLORS["border"],
        command=app.start_all,
    )
    app.start_all_btn.pack(fill="x", pady=(0, 4))
    app.stop_btn = ctk.CTkButton(
        action,
        text="Stop",
        height=30,
        font=app._font_ui,
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        state="disabled",
        command=app.stop,
    )
    app.stop_btn.pack(fill="x")

    progress_box = ctk.CTkFrame(root, fg_color=COLORS["panel"], corner_radius=10)
    progress_box.pack(fill="x", pady=(0, 8))

    app.file_progress_label = ctk.CTkLabel(
        progress_box,
        text="File: —",
        anchor="w",
        font=app._font_ui,
        text_color=COLORS["muted"],
    )
    app.file_progress_label.pack(fill="x", padx=12, pady=(8, 2))
    app.file_bar = ctk.CTkProgressBar(
        progress_box,
        height=14,
        progress_color=COLORS["accent"],
        fg_color=COLORS["panel2"],
    )
    app.file_bar.pack(fill="x", padx=12, pady=(0, 6))
    app.file_bar.set(0)

    app.job_progress_label = ctk.CTkLabel(
        progress_box,
        text="Job: —",
        anchor="w",
        font=app._font_ui,
        text_color=COLORS["muted"],
    )
    app.job_progress_label.pack(fill="x", padx=12, pady=(0, 2))
    app.job_bar = ctk.CTkProgressBar(
        progress_box,
        height=14,
        progress_color=COLORS["ok"],
        fg_color=COLORS["panel2"],
    )
    app.job_bar.pack(fill="x", padx=12, pady=(0, 6))
    app.job_bar.set(0)

    savings = ctk.CTkFrame(progress_box, fg_color="transparent")
    savings.pack(fill="x", padx=12, pady=(0, 10))
    savings.grid_columnconfigure(0, weight=1)
    savings.grid_columnconfigure(1, weight=1)
    savings.grid_columnconfigure(2, weight=1)

    app.last_course_label = ctk.CTkLabel(
        savings,
        text="Last course: —",
        anchor="w",
        font=app._font_ui,
        text_color=COLORS["text"],
    )
    app.last_course_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    app.session_freed_label = ctk.CTkLabel(
        savings,
        text="Session freed: 0 MiB",
        anchor="w",
        font=app._font_ui_bold,
        text_color=COLORS["ok"],
    )
    app.session_freed_label.grid(row=0, column=1, sticky="ew", padx=(0, 8))
    app.session_rate_label = ctk.CTkLabel(
        savings,
        text="0%",
        anchor="e",
        font=app._font_ui,
        text_color=COLORS["muted"],
    )
    app.session_rate_label.grid(row=0, column=2, sticky="ew")

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
        font=app._font_ui_bold,
        text_color=COLORS["text"],
    ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
    app.app_log = ctk.CTkTextbox(
        app_box,
        font=app._font_mono,
        fg_color=COLORS["panel2"],
        text_color=COLORS["text"],
        wrap="word",
    )
    app.app_log.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    ff_box = ctk.CTkFrame(logs, fg_color=COLORS["panel"], corner_radius=10)
    ff_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    ff_box.grid_rowconfigure(2, weight=1)
    ff_box.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        ff_box,
        text="FFmpeg",
        font=app._font_ui_bold,
        text_color=COLORS["text"],
    ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
    app.ff_live = ctk.CTkLabel(
        ff_box,
        text="idle",
        anchor="w",
        font=app._font_mono_sm,
        text_color=COLORS["accent"],
    )
    app.ff_live.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 2))
    app.ff_log = ctk.CTkTextbox(
        ff_box,
        font=app._font_mono_sm,
        fg_color=COLORS["panel2"],
        text_color=COLORS["muted"],
        wrap="none",
    )
    app.ff_log.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))


def path_row(
    app: App,
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
        font=app._font_ui,
        text_color=COLORS["muted"],
    ).pack(side="left")
    entry = ctk.CTkEntry(
        row,
        textvariable=var,
        height=28,
        font=app._font_mono_sm,
        fg_color=COLORS["panel2"],
        border_color=COLORS["border"],
    )
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
    btn = ctk.CTkButton(
        row,
        text="Browse…",
        width=88,
        height=28,
        font=app._font_ui,
        fg_color=COLORS["panel2"],
        hover_color=COLORS["border"],
        command=browse_cmd,
    )
    btn.pack(side="left")
    app._path_widgets.extend([entry, btn])


def settings_row(
    app: App,
    parent: ctk.CTkFrame,
    label: str,
    var: tk.StringVar,
) -> None:
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=10, pady=2)
    ctk.CTkLabel(
        row,
        text=label,
        width=100,
        anchor="w",
        font=app._font_ui,
        text_color=COLORS["muted"],
    ).pack(side="left")
    ctk.CTkEntry(
        row,
        textvariable=var,
        width=120,
        height=28,
        font=app._font_ui,
        fg_color=COLORS["panel2"],
        border_color=COLORS["border"],
    ).pack(side="left")
