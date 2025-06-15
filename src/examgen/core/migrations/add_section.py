from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine

from sqlalchemy.exc import OperationalError

from examgen.config import AppSettings

requires: set[str] = {"question"}
provides: set[str] = set()


def run() -> None:
    """Ensure ``section`` column exists in ``question`` table."""
    db_path = Path(
        AppSettings.load().data_db_path
        or Path.home() / "Documents" / "examgen.db"
    )
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    with eng.begin() as conn:
        cols = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info('question')")
        }
        if "section" not in cols:
            try:
                conn.exec_driver_sql(
                    "ALTER TABLE question ADD COLUMN section VARCHAR(255);"
                )
            except OperationalError:
                pass
