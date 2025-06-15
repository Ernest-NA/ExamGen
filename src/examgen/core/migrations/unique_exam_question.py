from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine

from examgen.config import AppSettings

requires: set[str] = {"exam_question"}
provides: set[str] = set()


def run() -> None:
    """Add unique index on (exam_id, question_id) if missing."""
    db_path = Path(
        AppSettings.load().data_db_path or Path.home() / "Documents" / "examgen.db"
    )
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    index_name = "uq_exam_question"
    with eng.begin() as conn:
        indexes = {
            row[1] for row in conn.exec_driver_sql("PRAGMA index_list('exam_question')")
        }
        if index_name not in indexes:
            conn.exec_driver_sql(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON exam_question (exam_id, question_id)"
            )
