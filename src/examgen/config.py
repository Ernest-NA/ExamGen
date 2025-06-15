from __future__ import annotations

from dataclasses import dataclass, asdict, fields
import json
from pathlib import Path
from platformdirs import user_config_dir

CFG_DIR = Path(user_config_dir("ExamGen"))
CFG_DIR.mkdir(parents=True, exist_ok=True)

# Base de datos inicial (vacía) si no existe ninguna
DEFAULT_DB = CFG_DIR / "examgen_initial_empty.db"
SETTINGS_FILE = CFG_DIR / "settings.json"


@dataclass
class AppSettings:
    theme: str = "dark"
    data_db_path: str | None = None
    debug_mode: bool = False

    @classmethod
    def load(cls) -> "AppSettings":
        if SETTINGS_FILE.exists():
            with SETTINGS_FILE.open(encoding="utf-8") as f:
                data = json.load(f)

            if "data_db_path" not in data and "data_dir" in data:
                data_dir = Path(data["data_dir"])
                data["data_db_path"] = str(data_dir / DEFAULT_DB.name)

            valid = {f.name for f in fields(cls)}
            clean = {k: v for k, v in data.items() if k in valid}
            return cls(**clean)
        return cls()

    def save(self) -> None:
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


settings = AppSettings.load()
