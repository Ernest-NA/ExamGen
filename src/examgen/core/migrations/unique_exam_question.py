from __future__ import annotations

from examgen.core.database import get_engine

requires: set[str] = {"exam_question"}
provides: set[str] = set()


def run() -> None:
    """Add unique index on (exam_id, question_id) if missing."""
    eng = get_engine()
    index_name = "uq_exam_question"
    with eng.begin() as conn:
        indexes = {
            row[1]
            for row in conn.exec_driver_sql(
                "PRAGMA index_list('exam_question')"
            )
        }
        if index_name not in indexes:
            conn.exec_driver_sql(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
                "ON exam_question (exam_id, question_id)"
            )
