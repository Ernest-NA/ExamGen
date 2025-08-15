from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json

from flask import Blueprint, render_template, request, redirect, url_for, abort
from sqlalchemy import text  # type: ignore

from examgen_web.infra.db import get_session
from examgen_web.infra import services as domain_services

questions_bp = Blueprint("questions", __name__)

# ---- Helpers ----

def _domain_available(name: str) -> bool:
    return getattr(domain_services, name, None) is not None


def _section_columns(session) -> List[str]:
    try:
        return [r[1] for r in session.execute(text("PRAGMA table_info(section)")).fetchall()]
    except Exception:
        return []


def _question_columns(session) -> List[str]:
    try:
        return [r[1] for r in session.execute(text("PRAGMA table_info(question)")).fetchall()]
    except Exception:
        return []


def _get_section_fallback(session, section_id: int) -> Optional[Dict[str, Any]]:
    row = session.execute(text("SELECT * FROM section WHERE id = :id"), {"id": section_id}).mappings().one_or_none()
    return dict(row) if row else None


def _get_exam_id_for_section(session, section_id: int) -> Optional[int]:
    sec = _get_section_fallback(session, section_id)
    return int(sec["exam_id"]) if sec and "exam_id" in sec else None


def _get_question_fallback(session, question_id: int) -> Optional[Dict[str, Any]]:
    row = session.execute(text("SELECT * FROM question WHERE id = :id"), {"id": question_id}).mappings().one_or_none()
    return dict(row) if row else None


def _as_json_if_possible(value: str) -> str:
    """Si 'value' es JSON válido, lo dejamos. Si contiene ';;', lo convertimos a JSON array. En otro caso, lo devolvemos igual."""
    if not value:
        return value
    try:
        json.loads(value)
        return value
    except Exception:
        pass
    if ";;" in value:
        parts = [p.strip() for p in value.split(";;") if p.strip()]
        return json.dumps(parts, ensure_ascii=False)
    return value


def _insert_question_fallback(session, section_id: int, payload: Dict[str, Any]) -> Optional[int]:
    cols = set(_question_columns(session))
    if not cols:
        return None
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data: Dict[str, Any] = {"section_id": section_id} if "section_id" in cols else {}
    for k in ("stem","type","choices","answer","difficulty","tags","metadata"):
        if k in cols and k in payload:
            v = payload[k]
            if k in ("choices","tags"):
                v = _as_json_if_possible(v)
            data[k] = v
    if "created_at" in cols:
        data["created_at"] = now
    if "updated_at" in cols:
        data["updated_at"] = now
    if not data:
        return None
    keys = list(data.keys())
    placeholders = [f":{k}" for k in keys]
    session.execute(text(f"INSERT INTO question ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"), data)
    session.commit()
    try:
        rid = session.execute(text("SELECT last_insert_rowid()")).scalar()
        return int(rid) if isinstance(rid, int) else None
    except Exception:
        try:
            rid = session.execute(text("SELECT id FROM question ORDER BY id DESC LIMIT 1")).scalar()
            return int(rid) if isinstance(rid, int) else None
        except Exception:
            return None


def _update_question_fallback(session, question_id: int, payload: Dict[str, Any]) -> None:
    cols = set(_question_columns(session))
    if not cols:
        return
    data: Dict[str, Any] = {}
    for k in ("stem","type","choices","answer","difficulty","tags","metadata"):
        if k in cols and (k in payload):
            v = payload[k]
            if k in ("choices","tags"):
                v = _as_json_if_possible(v)
            data[k] = v
    if "updated_at" in cols:
        data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not data:
        return
    sets = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["qid"] = question_id
    session.execute(text(f"UPDATE question SET {sets} WHERE id = :qid"), data)
    session.commit()

# ---- Endpoints ----

@questions_bp.get("/sections/<int:section_id>/questions/new")
def new_question(section_id: int):
    with get_session() as s:
        exam_id = _get_exam_id_for_section(s, section_id)
    if not isinstance(exam_id, int):
        abort(404)
    return render_template("question_form.html",
                           mode="create",
                           exam_id=exam_id,
                           section_id=section_id,
                           errors={},
                           form={"stem":"", "type":"mcq", "choices":"", "answer":"", "difficulty":"medium", "tags":""})


@questions_bp.post("/sections/<int:section_id>/questions")
def create_question(section_id: int):
    stem = (request.form.get("stem") or "").strip()
    qtype = (request.form.get("type") or "").strip() or "mcq"
    choices = (request.form.get("choices") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    difficulty = (request.form.get("difficulty") or "").strip() or "medium"
    tags = (request.form.get("tags") or "").strip()
    metadata = (request.form.get("metadata") or "").strip()

    errors = {}
    if not stem:
        errors["stem"] = "El enunciado es obligatorio."
    if errors:
        with get_session() as s:
            exam_id = _get_exam_id_for_section(s, section_id)
        return render_template("question_form.html",
                               mode="create", exam_id=exam_id, section_id=section_id,
                               errors=errors,
                               form={"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata}), 400

    with get_session() as s:
        if _domain_available("QuestionService"):
            try:
                svc = domain_services.get_question_service(s)
                payload = {"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata}
                svc.add_question(section_id, payload)  # type: ignore[attr-defined]
            except Exception:
                _insert_question_fallback(s, section_id, {"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata})
        else:
            _insert_question_fallback(s, section_id, {"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata})

        exam_id = _get_exam_id_for_section(s, section_id)

    if isinstance(exam_id, int):
        return redirect(url_for("exams.exam_detail", exam_id=exam_id))
    abort(400)


@questions_bp.get("/questions/<int:question_id>/edit")
def edit_question(question_id: int):
    with get_session() as s:
        q = _get_question_fallback(s, question_id)
        if not q:
            abort(404)
        sec_id = int(q["section_id"]) if "section_id" in q else None
        exam_id = _get_exam_id_for_section(s, sec_id) if sec_id is not None else None
    if not isinstance(exam_id, int):
        abort(404)
    form = {
        "stem": q.get("stem",""),
        "type": q.get("type","mcq"),
        "choices": q.get("choices",""),
        "answer": q.get("answer",""),
        "difficulty": q.get("difficulty","medium"),
        "tags": q.get("tags",""),
        "metadata": q.get("metadata",""),
    }
    return render_template("question_form.html", mode="edit", exam_id=exam_id, section_id=sec_id, question_id=question_id, errors={}, form=form)


@questions_bp.post("/questions/<int:question_id>")
def update_question(question_id: int):
    stem = (request.form.get("stem") or "").strip()
    qtype = (request.form.get("type") or "").strip() or "mcq"
    choices = (request.form.get("choices") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    difficulty = (request.form.get("difficulty") or "").strip() or "medium"
    tags = (request.form.get("tags") or "").strip()
    metadata = (request.form.get("metadata") or "").strip()

    errors = {}
    if not stem:
        errors["stem"] = "El enunciado es obligatorio."

    with get_session() as s:
        q = _get_question_fallback(s, question_id)
        if not q:
            abort(404)
        sec_id = int(q["section_id"]) if "section_id" in q else None
        exam_id = _get_exam_id_for_section(s, sec_id) if sec_id is not None else None

    if errors:
        return render_template("question_form.html", mode="edit", exam_id=exam_id, section_id=sec_id, question_id=question_id, errors=errors,
                               form={"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata}), 400

    with get_session() as s:
        if _domain_available("QuestionService"):
            try:
                svc = domain_services.get_question_service(s)
                payload = {"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata}
                svc.update_question(question_id, payload)  # type: ignore[attr-defined]
            except Exception:
                _update_question_fallback(s, question_id, {"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata})
        else:
            _update_question_fallback(s, question_id, {"stem": stem, "type": qtype, "choices": choices, "answer": answer, "difficulty": difficulty, "tags": tags, "metadata": metadata})

    if isinstance(exam_id, int):
        return redirect(url_for("exams.exam_detail", exam_id=exam_id))
    abort(400)
