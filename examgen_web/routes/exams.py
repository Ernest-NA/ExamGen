from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, render_template, request, redirect, url_for, abort
from sqlalchemy import text  # type: ignore

from examgen_web.infra.db import get_session
from examgen_web.infra import services as domain_services
from examgen_web.infra import history  # <- NUEVO

exams_bp = Blueprint("exams", __name__)

def _domain_available(name: str) -> bool:
    return getattr(domain_services, name, None) is not None

def _to_exam_dict(obj: Any) -> Dict[str, Any]:
    get = (lambda k, default=None:
           getattr(obj, k, getattr(obj, "get", lambda _k, d=None: d)(k, default)))
    return {
        "id": get("id"),
        "title": get("title"),
        "description": get("description"),
        "language": get("language"),
        "created_at": get("created_at"),
        "updated_at": get("updated_at"),
    }

# ---- Fallback EXAM ----

def _exam_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(exam)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []

def _list_exams_fallback(session) -> List[Dict[str, Any]]:
    cols = _exam_columns(session)
    if not cols:
        return []
    order = "created_at DESC" if "created_at" in cols else "id DESC" if "id" in cols else None
    sql = "SELECT * FROM exam" + (f" ORDER BY {order}" if order else "")
    return [dict(r) for r in session.execute(text(sql)).mappings().all()]

def _get_exam_fallback(session, exam_id: int) -> Optional[Dict[str, Any]]:
    cols = _exam_columns(session)
    if not cols:
        return None
    row = session.execute(text("SELECT * FROM exam WHERE id = :id"), {"id": exam_id}).mappings().one_or_none()
    return dict(row) if row else None

# ---- Section/Question fallback para render ----

def _section_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(section)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []

def _list_sections_fallback(session, exam_id: int) -> List[Dict[str, Any]]:
    cols = _section_columns(session)
    if not cols:
        return []
    order_by = '"order"' if "order" in cols else "id" if "id" in cols else None
    sql = "SELECT * FROM section WHERE exam_id = :eid"
    if order_by:
        sql += f" ORDER BY {order_by}"
    return [dict(r) for r in session.execute(text(sql), {"eid": exam_id}).mappings().all()]

def _question_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(question)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []

def _list_questions_fallback(session, section_id: int) -> List[Dict[str, Any]]:
    cols = _question_columns(session)
    if not cols:
        return []
    order_by = "id" if "id" in cols else None
    sql = "SELECT * FROM question WHERE section_id = :sid"
    if order_by:
        sql += f" ORDER BY {order_by}"
    return [dict(r) for r in session.execute(text(sql), {"sid": section_id}).mappings().all()]

# ---------- Endpoints ----------

@exams_bp.get("/exams")
def list_exams():
    with get_session() as s:
        exams: List[Dict[str, Any]] = []
        if _domain_available("ExamService"):
            try:
                svc = domain_services.get_exam_service(s)
                exams = [_to_exam_dict(e) for e in svc.list_exams()]  # type: ignore[attr-defined]
            except Exception:
                exams = _list_exams_fallback(s)
        else:
            exams = _list_exams_fallback(s)
    return render_template("exams_list.html", exams=exams)

@exams_bp.get("/exams/new")
def new_exam():
    return render_template("exam_form.html", errors={}, form={"title":"", "description":"", "language":"es-ES"})

@exams_bp.post("/exams")
def create_exam():
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    language = (request.form.get("language") or "").strip() or None

    errors = {}
    if not title:
        errors["title"] = "El título es obligatorio."
    if errors:
        return render_template("exam_form.html", errors=errors, form={"title": title, "description": description, "language": language or "es-ES"}), 400

    with get_session() as s:
        if _domain_available("ExamService"):
            try:
                svc = domain_services.get_exam_service(s)
                created = svc.create_exam({"title": title, "description": description, "language": language or "es-ES"})  # type: ignore[attr-defined]
                exam_id = getattr(created, "id", None)
                if exam_id is None:
                    rows = _list_exams_fallback(s)
                    exam_id = rows[0]["id"] if rows and "id" in rows[0] else None
            except Exception:
                cols = set(_exam_columns(s))
                if cols:
                    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    data = {}
                    if "title" in cols: data["title"] = title
                    if "description" in cols: data["description"] = description
                    if "language" in cols: data["language"] = language or "es-ES"
                    if "created_at" in cols: data["created_at"] = now
                    if "updated_at" in cols: data["updated_at"] = now
                    keys = list(data.keys()); placeholders = [f":{k}" for k in keys]
                    s.execute(text(f"INSERT INTO exam ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"), data)
                    s.commit()
                exam_id = s.execute(text("SELECT last_insert_rowid()")).scalar()
        else:
            cols = set(_exam_columns(s))
            if cols:
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                data = {}
                if "title" in cols: data["title"] = title
                if "description" in cols: data["description"] = description
                if "language" in cols: data["language"] = language or "es-ES"
                if "created_at" in cols: data["created_at"] = now
                if "updated_at" in cols: data["updated_at"] = now
                keys = list(data.keys()); placeholders = [f":{k}" for k in keys]
                s.execute(text(f"INSERT INTO exam ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"), data)
                s.commit()
            exam_id = s.execute(text("SELECT last_insert_rowid()")).scalar()

    if isinstance(exam_id, int):
        # Historian
        history.record_event(
            exam_id=exam_id, entity="exam", action="create", entity_id=exam_id,
            summary=title or f"Exam {exam_id}", before=None,
            after={"title": title, "description": description, "language": language or "es-ES"},
            extra=None
        )
        return redirect(url_for("exams.exam_detail", exam_id=exam_id))
    return redirect(url_for("exams.list_exams"))

@exams_bp.get("/exams/<int:exam_id>")
def exam_detail(exam_id: int):
    with get_session() as s:
        # Exam
        exam: Optional[Dict[str, Any]] = None
        if _domain_available("ExamService"):
            try:
                svc = domain_services.get_exam_service(s)
                e = svc.get_exam(exam_id)  # type: ignore[attr-defined]
                if e: exam = _to_exam_dict(e)
            except Exception:
                exam = _get_exam_fallback(s, exam_id)
        else:
            exam = _get_exam_fallback(s, exam_id)
        if not exam:
            abort(404)

        # Sections
        if _domain_available("SectionService"):
            try:
                ssvc = domain_services.get_section_service(s)
                sections = [dict(id=getattr(x, "id", None),
                                 exam_id=getattr(x, "exam_id", None),
                                 title=getattr(x, "title", None),
                                 order=getattr(x, "order", None))
                            for x in ssvc.list_sections(exam_id)]  # type: ignore[attr-defined]
            except Exception:
                sections = _list_sections_fallback(s, exam_id)
        else:
            sections = _list_sections_fallback(s, exam_id)

        # Questions por sección
        enriched_sections: List[Dict[str, Any]] = []
        for sec in sections:
            sid = sec.get("id")
            if sid is None:
                continue
            if _domain_available("QuestionService"):
                try:
                    qsvc = domain_services.get_question_service(s)
                    qlist = qsvc.list_questions(sid)  # type: ignore[attr-defined]
                    questions = [dict(
                        id=getattr(q, "id", None),
                        section_id=getattr(q, "section_id", None),
                        stem=getattr(q, "stem", getattr(q, "text", None)),
                        type=getattr(q, "type", None),
                        choices=getattr(q, "choices", None),
                        answer=getattr(q, "answer", None),
                        difficulty=getattr(q, "difficulty", None),
                        tags=getattr(q, "tags", None),
                    ) for q in qlist]
                except Exception:
                    questions = _list_questions_fallback(s, sid)
            else:
                questions = _list_questions_fallback(s, sid)
            sec = {**sec, "questions": questions}
            enriched_sections.append(sec)

    # Historian: últimos 25 eventos
    events = history.list_events_for_exam(exam_id, limit=25)
    return render_template("exam_detail.html", exam=exam, sections=enriched_sections, events=events)
