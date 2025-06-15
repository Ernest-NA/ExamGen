from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine

from examgen.config import AppSettings


def run() -> None:
    """Ensure ``section`` column exists in ``question`` table."""
    db_path = Path(
        AppSettings.load().data_db_path or Path.home() / "Documents" / "examgen.db"
    )
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    with eng.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info('question')")}
        if "section" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE question ADD COLUMN section VARCHAR(255);"
            )
