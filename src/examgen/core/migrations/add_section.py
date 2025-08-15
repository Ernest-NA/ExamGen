from __future__ import annotations

from sqlalchemy.exc import OperationalError

from examgen.core.database import get_engine

requires: set[str] = {"question"}
provides: set[str] = set()


def run() -> None:
    """Ensure ``section`` column exists in ``question`` table."""
    eng = get_engine()
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
