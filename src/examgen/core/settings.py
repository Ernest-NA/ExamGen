from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import sys
from pathlib import Path

SETTINGS_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "settings.json"

@dataclass
class AppSettings:
    theme: str = "dark"

    @classmethod
    def load(cls) -> "AppSettings":
        if SETTINGS_PATH.exists():
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                return cls(**json.load(f))
        return cls()

    def save(self) -> None:
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
