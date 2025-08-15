from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

# Carga .env si existe (no falla si no está)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# platformdirs es opcional; si no está, se usa ~/.examgen
try:
    from platformdirs import user_data_dir  # type: ignore
except Exception:
    user_data_dir = None  # type: ignore

APP_NAME = "ExamGen"


def _default_db_path() -> Path:
    if user_data_dir:
        base = Path(user_data_dir(APP_NAME))
    else:
        base = Path.home() / f".{APP_NAME.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    return base / "examgen.db"


def get_db_url() -> str:
    url = os.getenv("EXAMGEN_DB_URL", "").strip()
    if url:
        return url
    # Por defecto, SQLite en carpeta de datos local
    return f"sqlite:///{_default_db_path().as_posix()}"


def db_file_exists(db_url: str) -> bool:
    # Solo es determinístico para SQLite
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "", 1)
        return Path(path).exists()
    # Para otros motores, asumimos que existe (se validará con ping)
    return True


@dataclass(frozen=True)
class Settings:
    db_url: str


def load_settings() -> Settings:
    return Settings(db_url=get_db_url())
