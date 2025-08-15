from __future__ import annotations

from dataclasses import dataclass, asdict, fields
import json
from pathlib import Path
from platformdirs import user_config_dir, user_log_dir

CFG_DIR = Path(user_config_dir("ExamGen"))
CFG_DIR.mkdir(parents=True, exist_ok=True)

db_folder: str | None = None  # carpeta elegida por usuario
DEFAULT_DB = CFG_DIR / "examgen_initial_empty.db"


def db_path() -> Path:
    return Path(db_folder) / "examgen.db" if db_folder else DEFAULT_DB

SETTINGS_FILE = CFG_DIR / "settings.json"


@dataclass
class AppSettings:
    theme: str = "dark"
    db_folder: str | None = None
    debug_mode: bool = False

    @classmethod
    def load(cls) -> "AppSettings":
        if SETTINGS_FILE.exists():
            with SETTINGS_FILE.open(encoding="utf-8") as f:
                data = json.load(f)

            if "db_folder" not in data:
                if "data_db_path" in data:
                    data["db_folder"] = str(Path(data["data_db_path"]).parent)
                elif "data_dir" in data:
                    data["db_folder"] = data["data_dir"]

            valid = {f.name for f in fields(cls)}
            clean = {k: v for k, v in data.items() if k in valid}
            return cls(**clean)
        return cls()

    def save(self) -> None:
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)


settings = AppSettings.load()
db_folder = settings.db_folder
