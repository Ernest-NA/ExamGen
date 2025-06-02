from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from examgen.models import (
    SessionLocal,
    Attempt,
    AttemptQuestion,
    Question,
    ExamQuestion,
    SelectorTypeEnum,
    Subject,
)


@dataclass(slots=True)
class ExamConfig:
    exam_id: int
    subject: str
    subject_id: int
    selector_type: SelectorTypeEnum
    num_questions: int | None
    error_threshold: int | None
    time_limit: int


def _select_random(
    session: Session, exam_id: int, limit: int, subject_id: int | None = None
) -> List[Question]:
    attempts_sub = (
        select(
            AttemptQuestion.question_id,
            func.count(AttemptQuestion.id).label("attempts_count"),
        )
        .group_by(AttemptQuestion.question_id)
        .subquery()
    )
    stmt = (
        select(Question)
        .join(ExamQuestion, ExamQuestion.question_id == Question.id)
        .outerjoin(attempts_sub, attempts_sub.c.question_id == Question.id)
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(func.coalesce(attempts_sub.c.attempts_count, 0).asc(), func.random())
        .limit(limit)
    )
    questions = list(session.scalars(stmt))
    if not questions and subject_id is not None:
        questions = (
            session.query(Question)
            .filter(Question.subject_id == subject_id)
            .order_by(func.random())
            .limit(limit)
            .all()
        )
    return questions


def _select_by_errors(
    session: Session, exam_id: int, limit: int, subject_id: int | None = None
) -> List[Question]:
    error_sub = (
        select(
            AttemptQuestion.question_id,
            func.count(AttemptQuestion.id).label("errors_count"),
        )
        .where(AttemptQuestion.is_correct.is_(False))
        .group_by(AttemptQuestion.question_id)
        .subquery()
    )
    attempts_sub = (
        select(
            AttemptQuestion.question_id,
            func.count(AttemptQuestion.id).label("attempts_count"),
        )
        .group_by(AttemptQuestion.question_id)
        .subquery()
    )
    stmt = (
        select(
            Question,
            func.coalesce(error_sub.c.errors_count, 0).label("errors"),
            func.coalesce(attempts_sub.c.attempts_count, 0).label("attempts"),
        )
        .join(ExamQuestion, ExamQuestion.question_id == Question.id)
        .outerjoin(error_sub, error_sub.c.question_id == Question.id)
        .outerjoin(attempts_sub, attempts_sub.c.question_id == Question.id)
        .filter(ExamQuestion.exam_id == exam_id)
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


def create_attempt(config: ExamConfig) -> Attempt:
    """Persist a new Attempt with its questions."""
    with SessionLocal() as session:
        if config.exam_id == 0:
            exam_id = (
                session.query(ExamQuestion.exam_id)
                .join(Question, ExamQuestion.question_id == Question.id)
                .join(Subject, Question.subject_id == Subject.id)
                .filter(Subject.name == config.subject)
                .limit(1)
                .scalar()
            )
            if not exam_id:
                raise ValueError(
                    f'No hay preguntas para la materia "{config.subject}"'
                )
            config.exam_id = exam_id

        attempt = Attempt(
            exam_id=config.exam_id,
            subject=config.subject,
            selector_type=config.selector_type,
            num_questions=config.num_questions,
            error_threshold=config.error_threshold,
            time_limit=config.time_limit,
            started_at=datetime.utcnow(),
        )
        session.add(attempt)

        if config.selector_type is SelectorTypeEnum.ALEATORIO:
            questions = _select_random(
                session, config.exam_id, config.num_questions or 0, config.subject_id
            )
        else:
            threshold = config.error_threshold or 0
            questions = _select_by_errors(
                session, config.exam_id, threshold, config.subject_id
            )

        if not questions:
            questions = (
                session.query(Question)
                .join(Subject, Question.subject_id == Subject.id)
                .filter(Subject.name == config.subject)
                .order_by(func.random())
                .limit(config.num_questions or 0)
                .all()
            )

        if not questions:
            raise ValueError(
                f'No hay preguntas para la materia "{config.subject}"'
            )

        for q in questions:
            attempt.questions.append(AttemptQuestion(question=q))

        session.commit()
        session.refresh(attempt)
        # populate questions to avoid DetachedInstanceError after closing session
        attempt.questions  # noqa: B018 - intentional attribute access for loading
        session.expunge(attempt)
        return attempt


def evaluate_attempt(attempt_id: int) -> Attempt:
    """Evaluate an attempt and store the score."""
    with SessionLocal() as session:
        stmt = (
            select(Attempt)
            .options(joinedload(Attempt.questions).joinedload(AttemptQuestion.question))
            .filter_by(id=attempt_id)
        )
        attempt = session.scalars(stmt).one()

        total = 0
        for aq in attempt.questions:
            correct = next(
                (opt.text for opt in aq.question.options if opt.is_correct), None
            )
            aq.is_correct = aq.selected_option == correct
            aq.score = 1 if aq.is_correct else 0
            total += aq.score

        attempt.score = total
        if attempt.ended_at is None:
            attempt.ended_at = datetime.utcnow()

        session.commit()
        session.refresh(attempt)
        return attempt


if __name__ == "__main__":
    cfg = ExamConfig(
        exam_id=1,
        subject="Demo",
        subject_id=1,
        selector_type=SelectorTypeEnum.ALEATORIO,
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
