from __future__ import annotations

import itertools
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List

from flask import (
    Blueprint,
    Response,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

from ..utils.audit import append_event

bp = Blueprint("player", __name__)

# In-memory attempts store used when domain services are unavailable.
_ATTEMPTS: Dict[int, Dict[str, Any]] = {}
_ATTEMPT_COUNTER = itertools.count(1)


# --- Helpers -----------------------------------------------------------------

def _sample_questions() -> List[Dict[str, Any]]:
    """Return a static set of questions used as fallback."""
    return [
        {
            "id": 1,
            "prompt": "¿Cuánto es 2 + 2?",
            "options": [
                {"letter": "A", "text": "4", "is_correct": True},
                {"letter": "B", "text": "5", "is_correct": False},
            ],
        }
    ]


def _create_attempt(exam_id: int) -> Dict[str, Any]:
    """Create an attempt using domain service or fallback questions."""
    try:
        from src.examgen.core.services import exam_service  # type: ignore
        from src.examgen.core import models as m  # type: ignore

        config = exam_service.ExamConfig(
            exam_id=exam_id,
            subject="Demo",
            subject_id=1,
            selector_type=m.SelectorTypeEnum.ALEATORIO,
            num_questions=1,
            error_threshold=None,
            time_limit=1,
        )
        att = exam_service.create_attempt(config)
        questions = []
        for aq in att.questions:
            opts = [
                {
                    "letter": letter,
                    "text": opt.text,
                    "is_correct": getattr(opt, "is_correct", False),
                }
                for letter, opt in zip("ABCDE", aq.question.options)
            ]
            questions.append(
                {
                    "id": aq.question.id,
                    "prompt": aq.question.prompt,
                    "options": opts,
                }
            )
    except Exception:
        questions = _sample_questions()
    attempt_id = next(_ATTEMPT_COUNTER)
    time_limit = getattr(locals().get("att", None), "time_limit", 0)
    attempt = {
        "id": attempt_id,
        "exam_id": exam_id,
        "questions": questions,
        "answers": {},
        "started_at": datetime.utcnow(),
        "score": None,
        "time_limit": time_limit,
    }
    _ATTEMPTS[attempt_id] = attempt
    session["attempt_id"] = attempt_id
    append_event("exam.started", exam_id=exam_id, attempt_id=attempt_id)
    return attempt


def _current_attempt(exam_id: int) -> Dict[str, Any]:
    attempt_id = session.get("attempt_id")
    if attempt_id and attempt_id in _ATTEMPTS:
        return _ATTEMPTS[attempt_id]
    return _create_attempt(exam_id)


def _evaluate_attempt(attempt: Dict[str, Any]) -> None:
    correct = 0
    for q in attempt["questions"]:
        correct_set = {o["letter"] for o in q["options"] if o["is_correct"]}
        sel = attempt["answers"].get(q["id"], "")
        if len(correct_set) == 1:
            is_correct = sel in correct_set
        else:
            is_correct = set(sel) == correct_set
        q["is_correct"] = is_correct
        if is_correct:
            correct += 1
    attempt["score"] = correct
    attempt["ended_at"] = datetime.utcnow()


# --- Routes -------------------------------------------------------------------

@bp.route("/exams/<int:exam_id>/take", methods=["GET", "POST"])
def take_exam(exam_id: int) -> str:
    attempt = _current_attempt(exam_id)
    questions = attempt["questions"]
    idx = int(request.form.get("idx", 0))
    if request.method == "POST":
        answer = request.form.get("answer", "")
        qid = questions[idx]["id"]
        attempt["answers"][qid] = answer
        append_event(
            "exam.answered", exam_id=exam_id, attempt_id=attempt["id"], question_id=qid
        )
        if idx + 1 >= len(questions) or request.form.get("action") == "finish":
            _evaluate_attempt(attempt)
            append_event("exam.finished", exam_id=exam_id, attempt_id=attempt["id"])
            return redirect(url_for("player.show_attempt", attempt_id=attempt["id"]))
        idx += 1
    question = questions[idx]
    progress = f"Pregunta {idx + 1}/{len(questions)}"
    return render_template(
        "exams/take.html",
        attempt=attempt,
        question=question,
        idx=idx,
        progress=progress,
    )


@bp.get("/attempts/<int:attempt_id>")
def show_attempt(attempt_id: int) -> str:
    attempt = _ATTEMPTS.get(attempt_id)
    if not attempt:
        return "Intento no encontrado", 404
    return render_template("attempts/detail.html", attempt=attempt)


def _stream_json(records: Iterable[Dict[str, Any]]) -> Iterable[str]:
    yield "["
    first = True
    for rec in records:
        if not first:
            yield ","
        yield json.dumps(rec, ensure_ascii=False)
        first = False
    yield "]"


@bp.get("/attempts/<int:attempt_id>.json")
def export_attempt_json(attempt_id: int) -> Response:
    attempt = _ATTEMPTS.get(attempt_id)
    if not attempt:
        return Response("{}", mimetype="application/json")
    append_event("attempt.exported", attempt_id=attempt_id, fmt="json")
    records = [
        {
            "question": q["prompt"],
            "answer": attempt["answers"].get(q["id"], ""),
            "correct": "".join(
                o["letter"] for o in q["options"] if o["is_correct"]
            ),
            "is_correct": q.get("is_correct", False),
        }
        for q in attempt["questions"]
    ]
    return Response(
        stream_with_context(_stream_json(records)), mimetype="application/json"
    )


def _stream_csv(records: Iterable[Dict[str, Any]]) -> Iterable[str]:
    rows = list(records)
    if not rows:
        yield ""
        return
    headers = list(rows[0].keys())
    yield ",".join(headers) + "\n"
    for row in rows:
        vals = [str(row.get(h, "")) for h in headers]
        yield ",".join(vals) + "\n"


@bp.get("/attempts/<int:attempt_id>.csv")
def export_attempt_csv(attempt_id: int) -> Response:
    attempt = _ATTEMPTS.get(attempt_id)
    if not attempt:
        return Response("", mimetype="text/csv")
    append_event("attempt.exported", attempt_id=attempt_id, fmt="csv")
    records = [
        {
            "question": q["prompt"],
            "answer": attempt["answers"].get(q["id"], ""),
            "correct": "".join(
                o["letter"] for o in q["options"] if o["is_correct"]
            ),
            "is_correct": q.get("is_correct", False),
        }
        for q in attempt["questions"]
    ]
    return Response(
        stream_with_context(_stream_csv(records)),
        mimetype="text/csv; charset=utf-8",
    )
