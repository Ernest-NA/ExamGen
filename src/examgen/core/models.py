from __future__ import annotations

"""
ExamGen – ORM models (single‑table inheritance con columna `type` + JSON `meta`).
Ejecuta:       python -m examgen.models
para crear / actualizar examgen.db en la raíz del proyecto.
"""

# ruff: noqa: E402

import datetime as _dt
from enum import Enum as _Enum
from pathlib import Path
from typing import List

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    Enum as SQLAEnum,
    inspect,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class SelectorTypeEnum(str, _Enum):
    ALEATORIO = "ALEATORIO"
    ERRORES = "ERRORES"


# -----------------------------------------------------------------------------
# Declarative base común
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_dt.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=_dt.datetime.utcnow,
        onupdate=_dt.datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        attrs = (
            f"{k}={getattr(self, k)!r}"
            for k in self.__mapper__.columns.keys()
            if k not in {"created_at", "updated_at"}
        )
        return f"<{self.__class__.__name__} {' '.join(attrs)}>"

    # -----------------------------------------------------------------------------


# Entidades de dominio
# -----------------------------------------------------------------------------
class Subject(Base):
    __tablename__ = "subject"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

    questions: Mapped[List["Question"]] = relationship(
        back_populates="subject", foreign_keys="Question.subject_id"
    )


class Question(Base):
    """Pregunta base: columna `type` discrimina el subtipo."""

    __tablename__ = "question"

    prompt: Mapped[str] = mapped_column(Text(), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text())
    difficulty: Mapped[int] = mapped_column(Integer, default=0)  # 0‑5

    type: Mapped[str] = mapped_column(String(30), default="MCQ", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    # relaciones de materia y referencia
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"), nullable=False)
    subject: Mapped[Subject] = relationship(
        back_populates="questions", foreign_keys=[subject_id]
    )
    reference: Mapped[str | None] = mapped_column(String(200))
    section: Mapped[str | None] = mapped_column(String(255))

    option_e: Mapped[str | None] = mapped_column(Text())
    is_e_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    options: Mapped[List["AnswerOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "BASE"}

    @property
    def options_dict(self) -> dict[str, "AnswerOption"]:
        """Return a mapping letter→AnswerOption for quick access."""
        return {letter: opt for letter, opt in zip("ABCDE", self.options)}


class MCQQuestion(Question):
    __mapper_args__ = {"polymorphic_identity": "MCQ"}


class TrueFalseQuestion(Question):
    __mapper_args__ = {"polymorphic_identity": "TF"}


class AnswerOption(Base):
    __tablename__ = "answer_option"

    text: Mapped[str] = mapped_column(Text(), nullable=False)
    answer: Mapped[str | None] = mapped_column(Text())  # NUEVO
    explanation: Mapped[str | None] = mapped_column(Text())  # NUEVO
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    question: Mapped[Question] = relationship(back_populates="options")


class ExamQuestion(Base):
    __tablename__ = "exam_question"
    __table_args__ = (UniqueConstraint("exam_id", "question_id"),)

    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship()


class Exam(Base):
    __tablename__ = "exam"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    questions: Mapped[List[ExamQuestion]] = relationship(
        backref="exam", cascade="all, delete-orphan", order_by=ExamQuestion.order
    )
    attempts: Mapped[List["Attempt"]] = relationship(back_populates="exam")


class Attempt(Base):
    __tablename__ = "attempt"

    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exam.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    selector_type: Mapped[SelectorTypeEnum] = mapped_column(
        SQLAEnum(SelectorTypeEnum), nullable=False
    )
    num_questions: Mapped[int | None] = mapped_column(Integer)
    error_threshold: Mapped[int | None] = mapped_column(Integer)
    time_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_dt.datetime.utcnow, nullable=False
    )
    ended_at: Mapped[_dt.datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int | None] = mapped_column(Integer)

    exam: Mapped["Exam"] = relationship(back_populates="attempts")
    questions: Mapped[List["AttemptQuestion"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class AttemptQuestion(Base):
    __tablename__ = "attempt_question"

    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempt.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    selected_option: Mapped[str | None] = mapped_column(String(200))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[int | None] = mapped_column(Integer)

    attempt: Mapped["Attempt"] = relationship(back_populates="questions")
    question: Mapped[Question] = relationship()


def _migrate_attempt_subject_column(engine: Engine) -> None:
    """Add ``subject`` column to ``attempt`` table if missing."""
    with engine.begin() as con:
        cols = {row[1] for row in con.exec_driver_sql("PRAGMA table_info('attempt')")}
        if "subject" not in cols:
            con.exec_driver_sql("ALTER TABLE attempt ADD COLUMN subject TEXT")


def _add_option_e(engine: Engine) -> None:
    """Add option_e and is_e_correct columns if missing."""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("question")}
    alter = []
    if "option_e" not in cols:
        alter.append("ADD COLUMN option_e TEXT")
    if "is_e_correct" not in cols:
        alter.append("ADD COLUMN is_e_correct BOOLEAN DEFAULT 0")
    if alter:
        with engine.begin() as conn:
            for stmt in alter:
                conn.exec_driver_sql(f"ALTER TABLE question {stmt}")


def _add_section(engine: Engine) -> None:
    """Add section column to question table if missing."""
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("question")}
    if "section" not in cols:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE question ADD COLUMN section VARCHAR(255)"
            )


def _make_attempt_exam_nullable(engine: Engine) -> None:
    """Drop NOT NULL constraint from ``attempt.exam_id`` if present."""
    with engine.begin() as con:
        info = con.exec_driver_sql("PRAGMA table_info('attempt')").fetchall()
        exam_col = next((row for row in info if row[1] == "exam_id"), None)
        if exam_col and exam_col[3]:
            Attempt.__table__.c.exam_id.nullable = True
            cols = ", ".join(row[1] for row in info)
            con.exec_driver_sql("PRAGMA foreign_keys = OFF")
            con.exec_driver_sql("ALTER TABLE attempt RENAME TO attempt_old")
            Attempt.__table__.create(bind=con)
            con.exec_driver_sql(
                f"INSERT INTO attempt ({cols}) SELECT {cols} FROM attempt_old"
            )
            con.exec_driver_sql("DROP TABLE attempt_old")
            con.exec_driver_sql("PRAGMA foreign_keys = ON")


def _create_examiner_tables(engine: Engine) -> None:
    insp = inspect(engine)
    tables = []
    if not insp.has_table("attempt"):
        tables.append(Attempt.__table__)
    if not insp.has_table("attempt_question"):
        tables.append(AttemptQuestion.__table__)
    if tables:
        Base.metadata.create_all(bind=engine, tables=tables)

    _migrate_attempt_subject_column(engine)
    _add_option_e(engine)
    _add_section(engine)
    _make_attempt_exam_nullable(engine)


# -----------------------------------------------------------------------------
# Utilidades de BD
# -----------------------------------------------------------------------------


def get_engine(db_path: str | Path = "examgen.db"):
    return create_engine(f"sqlite:///{db_path}", echo=False, future=True)


def init_db(db_path: str | Path = "examgen.db") -> None:
    from examgen.core.database import set_engine, get_engine, init_db as _init

    set_engine(Path(db_path))
    engine = get_engine()

    _init(engine)

    with engine.begin() as con:
        con.exec_driver_sql("PRAGMA foreign_keys = ON")

        existing_cols = {
            tbl: {row[1] for row in con.exec_driver_sql(f"PRAGMA table_info({tbl})")}
            for tbl in ("question", "answer_option")
        }

        # columna reference (texto) — solo si no existe ninguna variante
        if (
            "reference" not in existing_cols["question"]
            and "reference_id" not in existing_cols["question"]
        ):
            con.exec_driver_sql("ALTER TABLE question ADD COLUMN reference TEXT")

        # columnas nuevas en answer_option (por si no estaban)
        for col_sql in ("answer TEXT", "explanation TEXT"):
            col_name = col_sql.split()[0]
            if col_name not in existing_cols["answer_option"]:
                con.exec_driver_sql(f"ALTER TABLE answer_option ADD COLUMN {col_sql}")

    print(f"✔️  Database initialised / migrated at {db_path}")


if __name__ == "__main__":
    init_db()
