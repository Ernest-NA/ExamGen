from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import sys
from pathlib import Path

SETTINGS_PATH = (
    Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    / "settings.json"
)


@dataclass
class AppSettings:
    theme: str = "dark"
    data_db_path: str | None = None

    @classmethod
    def load(cls) -> "AppSettings":
        if SETTINGS_PATH.exists():
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            allowed = {k: data[k] for k in ("theme", "data_db_path") if k in data}
            return cls(**allowed)
        return cls()

    def save(self) -> None:
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
