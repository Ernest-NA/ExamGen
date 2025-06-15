from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine

from examgen.config import AppSettings
from examgen.core.models import Base

# No prerequisites: this migration creates the initial schema
requires: set[str] = set()
# Tables provided after running this migration
provides: set[str] = set(Base.metadata.tables)


def run() -> None:
    """Create all tables if they don't exist."""
    db_path = Path(
        AppSettings.load().data_db_path
        or Path.home() / "Documents" / "examgen.db"
    )
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(eng)
