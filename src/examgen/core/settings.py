from __future__ import annotations

from dataclasses import dataclass, asdict
import dataclasses
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
            with SETTINGS_PATH.open(encoding="utf-8") as f:
                data = json.load(f)

            # --- compatibilidad con versiones anteriores ---
            if "data_db_path" not in data and "data_dir" in data:
                data["data_db_path"] = str(Path(data["data_dir"]) / "examgen.db")

            # descartar claves desconocidas
            valid = {f.name for f in dataclasses.fields(cls)}
            clean = {k: v for k, v in data.items() if k in valid}

            return cls(**clean)

        return cls()

    def save(self) -> None:
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
