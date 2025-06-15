from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)

from examgen.config import AppSettings


def run() -> None:
    """Fix attempt_question FK pointing to attempt.id."""
    db_path = Path(AppSettings.load().data_db_path or Path.home() / "Documents" / "examgen.db")
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    meta = MetaData()
    try:
        meta.reflect(bind=eng, resolve_fks=False)
    except sa.exc.NoSuchTableError:
        print(
            "NoSuchTableError durante reflect; puede que no exista ninguna "
            "tabla con FKs rotas. Continuando…"
        )
        return

    if "attempt_question" not in meta.tables:
        print("Tabla 'attempt_question' no existe; nada que migrar.")
        return

    # ---- verificar FK con PRAGMA (fiable incluso si falta attempt_old) ----
    with eng.connect() as conn:
        fk_rows = (
            conn.exec_driver_sql(
                "PRAGMA foreign_key_list('attempt_question');"
            )
            .mappings()
            .all()
        )
    bad_fk = any(row["table"] == "attempt_old" for row in fk_rows)
    if not bad_fk:
        print("FK ya es correcta; nada que migrar.")
        return

    with eng.begin() as conn:
        print("Migrando FK de attempt_question ...")
        conn.exec_driver_sql("ALTER TABLE attempt_question RENAME TO attempt_question_old;")

        meta2 = MetaData()
        Table(
            "attempt_question",
            meta2,
            Column("id", Integer, primary_key=True),
            Column(
                "attempt_id",
                Integer,
                ForeignKey("attempt.id", ondelete="CASCADE"),
                nullable=False,
            ),
            Column(
                "question_id",
                Integer,
                ForeignKey("question.id", ondelete="CASCADE"),
                nullable=False,
            ),
            Column("selected_option", String, nullable=True),
            Column("is_correct", Integer, nullable=True),
            Column("score", Integer, nullable=True),
            Column("created_at", String),
            Column("updated_at", String),
        )
        meta2.create_all(conn)

        conn.exec_driver_sql(
            """
            INSERT INTO attempt_question (id, attempt_id, question_id,
                                          selected_option, is_correct, score,
                                          created_at, updated_at)
            SELECT id, attempt_id, question_id,
                   selected_option, is_correct, score,
                   created_at, updated_at
            FROM attempt_question_old;
            """
        )

        conn.exec_driver_sql("DROP TABLE attempt_question_old;")
        print("Migración completada.")

