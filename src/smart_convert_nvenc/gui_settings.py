from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .paths import CoursePaths, resolve_course_paths


SETTINGS_SCHEMA = 1
SETTINGS_FILENAME = "settings.json"


def default_settings_path() -> Path:
    base = os.environ.get("SMART_CONVERT_APPDATA")
    if base:
        root = Path(base)
    elif os.name == "nt":
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return (root / "smart_convert_nvenc" / SETTINGS_FILENAME).resolve()


@dataclass
class GuiSettings:
    schema: int = SETTINGS_SCHEMA
    inbox: str = ""
    outbox: str = ""
    tmp: str = ""
    sample_sec: str = "20"
    min_savings: str = "0.10"
    cq_hevc: str = "28"
    cq_av1: str = "32"
    preset: str = "p6"
    codec: str = "auto"
    encoder: str = "gpu"
    skip_same_codec: bool = True

    def course_paths(self) -> CoursePaths:
        inbox = Path(self.inbox) if self.inbox.strip() else None
        outbox = Path(self.outbox) if self.outbox.strip() else None
        tmp = Path(self.tmp) if self.tmp.strip() else None
        if inbox is None and outbox is None and tmp is None:
            return resolve_course_paths()
        return resolve_course_paths(inbox=inbox, outbox=outbox, tmp=tmp)

    def with_paths(self, paths: CoursePaths) -> GuiSettings:
        return GuiSettings(
            schema=self.schema,
            inbox=str(paths.inbox),
            outbox=str(paths.outbox),
            tmp=str(paths.tmp),
            sample_sec=self.sample_sec,
            min_savings=self.min_savings,
            cq_hevc=self.cq_hevc,
            cq_av1=self.cq_av1,
            preset=self.preset,
            codec=self.codec,
            encoder=self.encoder,
            skip_same_codec=self.skip_same_codec,
        )


def load_gui_settings(path: Path | None = None) -> GuiSettings:
    settings_path = path or default_settings_path()
    if not settings_path.is_file():
        return GuiSettings().with_paths(resolve_course_paths())
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return GuiSettings().with_paths(resolve_course_paths())
    if not isinstance(data, dict):
        return GuiSettings().with_paths(resolve_course_paths())

    known = {f.name for f in fields(GuiSettings)}
    filtered = {
        k: v
        for k, v in data.items()
        if k in known and isinstance(v, (str, int, bool))
    }
    if "schema" in filtered and isinstance(filtered["schema"], str):
        try:
            filtered["schema"] = int(filtered["schema"])
        except ValueError:
            filtered["schema"] = SETTINGS_SCHEMA
    settings = GuiSettings(**filtered)  # type: ignore[arg-type]
    if not settings.inbox or not settings.outbox or not settings.tmp:
        return settings.with_paths(settings.course_paths())
    return settings


def save_gui_settings(settings: GuiSettings, path: Path | None = None) -> Path:
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    payload["schema"] = SETTINGS_SCHEMA
    settings_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return settings_path
