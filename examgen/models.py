from __future__ import annotations
"""examgen/models.py – ORM + migración idempotente para ExamGen.

Ejecuta: ``python -m examgen.models`` para crear o migrar la base de datos
SQLite ubicada en la carpeta de datos que indique el usuario.
"""
import datetime as _dt
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
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)

# -----------------------------------------------------------------------------
# Declarative base común
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Incluye id autoincremental y timestamps de creación / actualización."""

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

    # repr útil para depuración ------------------------------------------------
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

    name:        Mapped[str]        = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

    questions: Mapped[List["Question"]] = relationship(
        back_populates="subject", foreign_keys="Question.subject_id"
    )


class Question(Base):
    """Pregunta base – `type` discrimina subtipo (MCQ / TF)."""

    __tablename__ = "question"

    prompt:       Mapped[str] = mapped_column(Text(), nullable=False)
    explanation:  Mapped[str | None] = mapped_column(Text())
    difficulty:   Mapped[int] = mapped_column(Integer, default=0)

    type: Mapped[str]  = mapped_column(String(30), default="MCQ", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    # materia
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"), nullable=False)
    subject:    Mapped[Subject] = relationship(back_populates="questions", foreign_keys=[subject_id])

    # referencia libre (ej.: "exam_1025")
    reference: Mapped[str | None] = mapped_column(String(200))

    options: Mapped[List["AnswerOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"polymorphic_on": type, "polymorphic_identity": "BASE"}


class MCQQuestion(Question):
    __mapper_args__ = {"polymorphic_identity": "MCQ"}


class TrueFalseQuestion(Question):
    __mapper_args__ = {"polymorphic_identity": "TF"}


class AnswerOption(Base):
    __tablename__ = "answer_option"

    text:        Mapped[str]        = mapped_column(Text(), nullable=False)
    answer:      Mapped[str | None] = mapped_column(Text())
    explanation: Mapped[str | None] = mapped_column(Text())
    is_correct:  Mapped[bool]       = mapped_column(Boolean, default=False)

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    question:    Mapped[Question] = relationship(back_populates="options")


class Exam(Base):
    __tablename__ = "exam"

    title:       Mapped[str]  = mapped_column(String(200), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    questions: Mapped[List["ExamQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.order"
    )
    attempts: Mapped[List["Attempt"]] = relationship(back_populates="exam")


class ExamQuestion(Base):
    __tablename__ = "exam_question"

    exam_id:     Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    order:       Mapped[int] = mapped_column(Integer, nullable=False)

    exam:     Mapped[Exam]     = relationship(back_populates="questions")
    question: Mapped[Question] = relationship()


class Attempt(Base):
    __tablename__ = "attempt"

    timestamp: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_dt.datetime.utcnow, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    user:    Mapped["auth.User"] = relationship(back_populates="attempts")  # type: ignore[name-defined]

    exam_id: Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False)
    exam:    Mapped[Exam] = relationship(back_populates="attempts")

    answers: Mapped[List["AttemptAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )

class AttemptAnswer(Base):
    __tablename__ = "attempt_answer"

    attempt_id:         Mapped[int] = mapped_column(ForeignKey("attempt.id"), nullable=False)
    question_id:        Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    selected_option_id: Mapped[int | None] = mapped_column(ForeignKey("answer_option.id"))
    is_correct:         Mapped[bool] = mapped_column(Boolean, default=False)

    attempt:         Mapped[Attempt]                = relationship(back_populates="answers")
    question:        Mapped[Question]               = relationship()
    selected_option: Mapped[AnswerOption | None]    = relationship()


# -----------------------------------------------------------------------------
# Utilidades de BD
# -----------------------------------------------------------------------------

def get_engine(db_path: str | Path = "examgen.db"):
    """Devuelve engine SQLite para la ruta indicada."""
    return create_engine(f"sqlite:///{db_path}", future=True)


def init_db(db_path: str | Path = "examgen.db") -> None:
    """Crea tablas que falten y añade columnas nuevas cuando sea necesario."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)  # crea tablas nuevas según modelos

    with engine.begin() as con:
        con.exec_driver_sql("PRAGMA foreign_keys = ON")

        # helper columnas existentes ------------------------------------------------
        def cols(tbl: str) -> set[str]:
            return {row[1] for row in con.exec_driver_sql(f"PRAGMA table_info({tbl})")}

        existing_tables = {
            row[0] for row in con.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

        # ---------- USER ---------------------------------------------------------
        if "user" not in existing_tables:
            auth.User.__table__.create(engine)
        else:
            ucols = cols("user")

            if "theme" not in ucols:
                con.exec_driver_sql(
                    "ALTER TABLE user ADD COLUMN theme TEXT DEFAULT 'dark'"
                )

            if "email" not in ucols:
                # SQLite no permite añadir UNIQUE directamente; se crea índice único aparte
                con.exec_driver_sql("ALTER TABLE user ADD COLUMN email TEXT")
                con.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_email ON user(email)"
                )

        # ---------- QUESTION -----------------------------------------------------
        qcols = cols("question")
        if "reference" not in qcols and "reference_id" not in qcols:
            con.exec_driver_sql("ALTER TABLE question ADD COLUMN reference TEXT")

        # ---------- ANSWER_OPTION -------------------------------------------------
        acols = cols("answer_option")
        for col_sql in ("answer TEXT", "explanation TEXT"):
            name = col_sql.split()[0]
            if name not in acols:
                con.exec_driver_sql(f"ALTER TABLE answer_option ADD COLUMN {col_sql}")

        acol = cols("attempt")
        if "user_id" not in acol:
            con.exec_driver_sql("ALTER TABLE attempt ADD COLUMN user_id INTEGER")
            # Foreign keys en SQLite se añaden implícitamente; índice opcional:
            con.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_attempt_user ON attempt(user_id)"
            )

    print(f"✔  Database up-to-date at {db_path}")


# -----------------------------------------------------------------------------
# CLI sencillo para pruebas
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
