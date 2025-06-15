from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List
import random

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload, with_polymorphic

from examgen.core import models as m
from examgen.core.database import SessionLocal


@dataclass(slots=True)
class ExamConfig:
    exam_id: int
    subject: str
    subject_id: int
    selector_type: m.SelectorTypeEnum
    num_questions: int | None
    error_threshold: int | None
    time_limit: int


def _select_random(
    session: Session, exam_id: int, limit: int, subject_id: int | None = None
) -> List[m.Question]:
    attempts_sub = (
        select(
            m.AttemptQuestion.question_id,
            func.count(m.AttemptQuestion.id).label("attempts_count"),
        )
        .group_by(m.AttemptQuestion.question_id)
        .subquery()
    )
    stmt = (
        select(m.Question)
        .distinct(m.Question.id)
        .join(m.ExamQuestion, m.ExamQuestion.question_id == m.Question.id)
        .outerjoin(attempts_sub, attempts_sub.c.question_id == m.Question.id)
        .filter(m.ExamQuestion.exam_id == exam_id)
        .order_by(func.coalesce(attempts_sub.c.attempts_count, 0).asc(), func.random())
        .limit(limit)
    )
    questions = list(session.scalars(stmt))
    if not questions and subject_id is not None:
        questions = (
            session.query(m.Question)
            .filter(m.Question.subject_id == subject_id)
            .order_by(func.random())
            .limit(limit)
            .all()
        )
    return questions


def _select_by_errors(
    session: Session, exam_id: int, limit: int, subject_id: int | None = None
) -> List[m.Question]:
    error_sub = (
        select(
            m.AttemptQuestion.question_id,
            func.count(m.AttemptQuestion.id).label("errors_count"),
        )
        .where(m.AttemptQuestion.is_correct.is_(False))
        .group_by(m.AttemptQuestion.question_id)
        .subquery()
    )
    attempts_sub = (
        select(
            m.AttemptQuestion.question_id,
            func.count(m.AttemptQuestion.id).label("attempts_count"),
        )
        .group_by(m.AttemptQuestion.question_id)
        .subquery()
    )
    stmt = (
        select(
            m.Question,
            func.coalesce(error_sub.c.errors_count, 0).label("errors"),
            func.coalesce(attempts_sub.c.attempts_count, 0).label("attempts"),
        )
        .distinct(m.Question.id)
        .join(m.ExamQuestion, m.ExamQuestion.question_id == m.Question.id)
        .outerjoin(error_sub, error_sub.c.question_id == m.Question.id)
        .outerjoin(attempts_sub, attempts_sub.c.question_id == m.Question.id)
        .filter(m.ExamQuestion.exam_id == exam_id)
        .order_by(
            func.coalesce(error_sub.c.errors_count, 0).desc(),
            func.coalesce(attempts_sub.c.attempts_count, 0).asc(),
        )
        .limit(limit)
    )
    results = session.execute(stmt).all()
    if not results or all(row.errors == 0 for row in results):
        return _select_random(session, exam_id, limit, subject_id)
    return [row.Question for row in results]


def create_attempt(config: ExamConfig) -> m.Attempt:
    """Persist a new Attempt with its questions."""
    with SessionLocal() as session:
        if config.exam_id == 0:
            stmt = (
                session.query(m.Question)
                .join(m.Subject, m.Question.subject_id == m.Subject.id)
                .filter(func.lower(m.Subject.name) == config.subject.lower())
                .order_by(func.random())
                .limit(config.num_questions or 0)
            )
            questions = stmt.all()
            if not questions:
                raise ValueError(f'No hay preguntas para la materia "{config.subject}"')
        else:
            if config.selector_type is m.SelectorTypeEnum.ALEATORIO:
                questions = _select_random(
                    session,
                    config.exam_id,
                    config.num_questions or 0,
                    config.subject_id,
                )
            else:
                threshold = config.error_threshold or 0
                questions = _select_by_errors(
                    session, config.exam_id, threshold, config.subject_id
                )

            if not questions:
                questions = (
                    session.query(m.Question)
                    .join(m.Subject, m.Question.subject_id == m.Subject.id)
                    .filter(func.lower(m.Subject.name) == config.subject.lower())
                    .order_by(func.random())
                    .limit(config.num_questions or 0)
                    .all()
                )

            if not questions:
                raise ValueError(f'No hay preguntas para la materia "{config.subject}"')

        # Remove duplicates and shuffle final question list
        questions = list({q.id: q for q in questions}.values())
        random.shuffle(questions)

        attempt = m.Attempt(
            exam_id=config.exam_id or None,
            subject=config.subject,
            selector_type=config.selector_type,
            num_questions=config.num_questions,
            error_threshold=config.error_threshold,
            time_limit=config.time_limit,
            started_at=datetime.utcnow(),
        )
        session.add(attempt)

        for q in questions:
            attempt.questions.append(m.AttemptQuestion(question=q))

        session.commit()

        q_poly = with_polymorphic(m.Question, "*")

        attempt = (
            session.query(m.Attempt)
            .options(
                selectinload(m.Attempt.questions)
                .selectinload(m.AttemptQuestion.question.of_type(q_poly))
                .selectinload(q_poly.MCQQuestion.options)
            )
            .filter_by(id=attempt.id)
            .one()
        )

        session.expunge_all()
        return attempt


def _compute_score(attempt: m.Attempt) -> int:
    """Calculate score and update AttemptQuestion entries."""
    total = 0
    for aq in attempt.questions:
        opts = list(zip("ABCDE", aq.question.options))
        correct_set = {
            letter for letter, opt in opts if getattr(opt, "is_correct", False)
        }
        sel = aq.selected_option or ""
        if len(correct_set) == 1:
            aq.is_correct = sel in correct_set
        else:
            aq.is_correct = set(sel) == correct_set
        aq.score = 1 if aq.is_correct else 0
        total += aq.score

    if attempt.ended_at is None:
        attempt.ended_at = datetime.utcnow()

    return total


def evaluate_attempt(attempt_id: int) -> m.Attempt:
    """Evaluate an attempt and store the score."""
    with SessionLocal() as s:
        attempt = (
            s.query(m.Attempt)
            .options(selectinload(m.Attempt.questions))
            .get(attempt_id)
        )
        if not attempt:
            raise ValueError("Attempt not found")

        correct = 0
        for aq in attempt.questions:
            q = aq.question
            correct_set = {l for l, opt in zip("ABCDE", q.options) if opt.is_correct}
            if aq.selected_option:
                if len(correct_set) == 1:
                    aq.is_correct = aq.selected_option in correct_set
                else:
                    aq.is_correct = set(aq.selected_option) == correct_set
            else:
                aq.is_correct = False
            if aq.is_correct:
                correct += 1

        attempt.score = correct
        if attempt.ended_at is None:
            attempt.ended_at = datetime.utcnow()

        s.commit()
        s.refresh(attempt)
        return attempt


if __name__ == "__main__":
    cfg = ExamConfig(
        exam_id=1,
        subject="Demo",
        subject_id=1,
        selector_type=m.SelectorTypeEnum.ALEATORIO,
        num_questions=3,
        error_threshold=None,
        time_limit=10,
    )
    att = create_attempt(cfg)
    for aq in att.questions:
        aq.selected_option = next(
            (opt.text for opt in aq.question.options if opt.is_correct), None
        )
    evaluate_attempt(att.id)
    print(f"Score: {att.score}")
