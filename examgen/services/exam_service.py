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
)


@dataclass(slots=True)
class ExamConfig:
    exam_id: int
    subject: str
    selector_type: SelectorTypeEnum
    num_questions: int | None
    error_threshold: int | None
    time_limit: int


def _select_random(session: Session, exam_id: int, limit: int) -> List[Question]:
    stmt = (
        select(Question)
        .join(ExamQuestion, ExamQuestion.question_id == Question.id)
        .filter(ExamQuestion.exam_id == exam_id)
        .order_by(func.random())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def _select_by_errors(
    session: Session, exam_id: int, limit: int
) -> List[Question]:
    error_count = func.count(AttemptQuestion.id)
    stmt = (
        select(Question, error_count.label("errors"))
        .join(ExamQuestion, ExamQuestion.question_id == Question.id)
        .outerjoin(
            AttemptQuestion,
            (AttemptQuestion.question_id == Question.id)
            & (AttemptQuestion.is_correct.is_(False)),
        )
        .filter(ExamQuestion.exam_id == exam_id)
        .group_by(Question.id)
        .order_by(error_count.desc())
        .limit(limit)
    )
    results = session.execute(stmt).all()
    if not results or all(row.errors == 0 for row in results):
        return _select_random(session, exam_id, limit)
    return [row.Question for row in results]


def create_attempt(config: ExamConfig) -> Attempt:
    """Persist a new Attempt with its questions."""
    with SessionLocal() as session:
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
            questions = _select_random(session, config.exam_id, config.num_questions or 0)
        else:
            threshold = config.error_threshold or 0
            questions = _select_by_errors(session, config.exam_id, threshold)

        for q in questions:
            attempt.questions.append(AttemptQuestion(question=q))

        session.commit()
        session.refresh(attempt)
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
