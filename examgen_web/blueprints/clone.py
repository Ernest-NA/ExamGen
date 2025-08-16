from __future__ import annotations

import json
from typing import Any, Dict, List

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Dominio primero; si los modelos no están disponibles, fallback vacío
try:  # pragma: no cover - se ejecuta en entornos sin el paquete
    from examgen.core import models as m
    from examgen.core.database import SessionLocal
except Exception:  # pragma: no cover - entorno mínimo
    m = None  # type: ignore
    SessionLocal = None  # type: ignore

from ..utils.clone_utils import _next_version, clone_question
from ..utils.audit import log_question_cloned

bp = Blueprint("questions", __name__)


@bp.get("/questions")
def list_questions() -> str:
    if SessionLocal is None or m is None:
        items: list[Any] = []
    else:
        with SessionLocal() as s:
            items = (
                s.query(m.MCQQuestion)
                .order_by(m.MCQQuestion.id.desc())
                .all()
            )
    return render_template("questions/list.html", items=items)


@bp.get("/questions/<int:qid>")
def question_detail(qid: int) -> str:
    if SessionLocal is None or m is None:
        return "Pregunta no disponible", 404
    with SessionLocal() as s:
        q = s.get(m.MCQQuestion, qid)
        if not q:
            return "Pregunta no encontrada", 404
        derived = (
            s.query(m.MCQQuestion)
            .filter(m.MCQQuestion.meta["cloned_from"].as_integer() == qid)
            .all()
        )
    return render_template(
        "questions/detail.html", question=q, derived=derived
    )


@bp.get("/questions/<int:qid>/clone")
def clone_form(qid: int) -> str:
    if SessionLocal is None or m is None:
        return "Pregunta no disponible", 404
    with SessionLocal() as s:
        q = s.get(m.MCQQuestion, qid)
        if not q:
            return "Pregunta no encontrada", 404
        subjects = (
            s.query(m.Subject).order_by(m.Subject.name).all()
        )
    version = _next_version(q.meta.get("version"))
    return render_template(
        "questions/clone.html",
        question=q,
        subjects=subjects,
        version=version,
    )


@bp.post("/questions/<int:qid>/clone")
def clone_post(qid: int):
    if SessionLocal is None or m is None:
        return "Pregunta no disponible", 404
    form = request.form
    with SessionLocal() as s:
        original = s.get(m.MCQQuestion, qid)
        if not original:
            return "Pregunta no encontrada", 404
        count = int(form.get("options_count", 0))
        options: List[Dict[str, Any]] = []
        for idx in range(count):
            options.append(
                {
                    "text": form.get(f"option_text_{idx}", ""),
                    "is_correct": form.get(f"option_correct_{idx}") == "on",
                    "answer": form.get(f"option_answer_{idx}") or None,
                    "explanation": form.get(
                        f"option_explanation_{idx}") or None,
                }
            )
        try:
            meta = json.loads(form.get("meta", "{}"))
        except json.JSONDecodeError:
            meta = {}
        overrides = {
            "prompt": form.get("prompt", ""),
            "explanation": form.get("explanation") or None,
            "difficulty": int(form.get("difficulty", original.difficulty)),
            "subject_id": int(form.get("subject_id", original.subject_id)),
            "version": form.get("version"),
            "meta": meta,
            "options": options,
        }
        new_q, changes = clone_question(s, original, overrides)
        s.commit()
    user = session.get("user")
    log_question_cloned(qid, new_q.id, user=user, changes=changes)
    return redirect(url_for("questions.question_detail", qid=new_q.id))
