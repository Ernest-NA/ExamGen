from __future__ import annotations

"""
ExamGen – ORM models (single‑table inheritance con columna `type` + JSON `meta`).
Ejecuta:       python -m examgen.models
para crear / actualizar examgen.db en la raíz del proyecto.
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
    mapped_column,
    relationship,
    Session,
)

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
    """Pregunta base: columna `type` discrimina el subtipo. """

    __tablename__ = "question"

    prompt:       Mapped[str] = mapped_column(Text(), nullable=False)
    explanation:  Mapped[str | None] = mapped_column(Text())
    difficulty:   Mapped[int] = mapped_column(Integer, default=0)  # 0‑5

    type: Mapped[str]  = mapped_column(String(30), default="MCQ", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    # relaciones de materia y referencia
    subject_id:   Mapped[int] = mapped_column(ForeignKey("subject.id"), nullable=False)
    subject:   Mapped[Subject] = relationship(back_populates="questions",  foreign_keys=[subject_id])
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

    text:        Mapped[str] = mapped_column(Text(), nullable=False)
    answer:      Mapped[str | None] = mapped_column(Text())        # NUEVO
    explanation: Mapped[str | None] = mapped_column(Text())        # NUEVO
    is_correct:  Mapped[bool] = mapped_column(Boolean, default=False)

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    question:    Mapped[Question] = relationship(back_populates="options")


class ExamQuestion(Base):
    __tablename__ = "exam_question"

    exam_id:     Mapped[int] = mapped_column(ForeignKey("exam.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"), nullable=False)
    order:       Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship()


class Exam(Base):
    __tablename__ = "exam"

    title:       Mapped[str] = mapped_column(String(200), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    questions: Mapped[List[ExamQuestion]] = relationship(
        backref="exam", cascade="all, delete-orphan", order_by=ExamQuestion.order
    )
    attempts:  Mapped[List["Attempt"]] = relationship(back_populates="exam")


class Attempt(Base):
    __tablename__ = "attempt"

    timestamp: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_dt.datetime.utcnow, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)

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

    attempt:         Mapped[Attempt]       = relationship(back_populates="answers")
    question:        Mapped[Question]      = relationship()
    selected_option: Mapped[AnswerOption | None] = relationship()

# -----------------------------------------------------------------------------
# Utilidades de BD
# -----------------------------------------------------------------------------

def get_engine(db_path: str | Path = "examgen.db"):
    return create_engine(f"sqlite:///{db_path}", echo=False, future=True)


def init_db(db_path: str | Path = "examgen.db") -> None:
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)        # crea tablas que falten

    with engine.begin() as con:
        con.exec_driver_sql("PRAGMA foreign_keys = ON")

        existing_cols = {
            tbl: {row[1] for row in con.exec_driver_sql(f"PRAGMA table_info({tbl})")}
            for tbl in ("question", "answer_option")
        }

        # columna reference (texto) — solo si no existe ninguna variante
        if ("reference" not in existing_cols["question"]
                and "reference_id" not in existing_cols["question"]):
            con.exec_driver_sql("ALTER TABLE question ADD COLUMN reference TEXT")

        # columnas nuevas en answer_option (por si no estaban)
        for col_sql in ("answer TEXT", "explanation TEXT"):
            col_name = col_sql.split()[0]
            if col_name not in existing_cols["answer_option"]:
                con.exec_driver_sql(f"ALTER TABLE answer_option ADD COLUMN {col_sql}")

    print(f"✔️  Database initialised / migrated at {db_path}")


if __name__ == "__main__":
    init_db()
