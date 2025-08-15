from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

from flask import Blueprint, render_template, request, abort
from sqlalchemy import text  # type: ignore

from examgen_web.infra.db import get_session
from examgen_web.infra import services as domain_services

preview_bp = Blueprint("preview", __name__)

# ---------- Helpers comunes (dominio + fallback) ----------

def _domain_available(name: str) -> bool:
    return getattr(domain_services, name, None) is not None

def _parse_json_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return []
        # JSON válido
        try:
            data = json.loads(v)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass
        # "A;;B;;C"
        if ";;" in v:
            return [p.strip() for p in v.split(";;") if p.strip()]
    return [str(value)]

def _get_exam_fallback(session, exam_id: int) -> Optional[Dict[str, Any]]:
    try:
        cols = [r[1] for r in session.execute(text("PRAGMA table_info(exam)")).fetchall()]
    except Exception:
        cols = []
    if not cols:
        return None
    row = session.execute(
        text("SELECT * FROM exam WHERE id = :id"), {"id": exam_id}
    ).mappings().one_or_none()
    return dict(row) if row else None

def _list_sections_fallback(session, exam_id: int) -> List[Dict[str, Any]]:
    cols = [r[1] for r in session.execute(text("PRAGMA table_info(section)")).fetchall()]
    order_by = '"order"' if "order" in cols else "id" if "id" in cols else None
    sql = "SELECT * FROM section WHERE exam_id = :eid"
    if order_by:
        sql += f" ORDER BY {order_by}"
    return [dict(r) for r in session.execute(text(sql), {"eid": exam_id}).mappings().all()]

def _list_questions_fallback(session, section_id: int) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM question WHERE section_id = :sid"
    return [dict(r) for r in session.execute(text(sql), {"sid": section_id}).mappings().all()]

def _normalize_question(q: Dict[str, Any]) -> Dict[str, Any]:
    # Asegurar claves esperadas por la vista/export
    return {
        "id": q.get("id"),
        "section_id": q.get("section_id"),
        "type": q.get("type") or q.get("qtype") or "mcq",
        "stem": q.get("stem") or q.get("text") or "",
        "choices": _parse_json_list(q.get("choices")),
        "answer": q.get("answer"),
        "difficulty": q.get("difficulty"),
        "tags": _parse_json_list(q.get("tags")),
        "rationale": q.get("rationale"),
        "metadata": q.get("metadata"),
    }

def _load_exam_tree(session, exam_id: int) -> Optional[Dict[str, Any]]:
    # Exam
    if _domain_available("ExamService"):
        try:
            esvc = domain_services.get_exam_service(session)
            e = esvc.get_exam(exam_id)  # type: ignore[attr-defined]
            if e:
                exam = {
                    "id": getattr(e, "id", None),
                    "title": getattr(e, "title", None),
                    "description": getattr(e, "description", None),
                    "language": getattr(e, "language", None),
                    "created_at": getattr(e, "created_at", None),
                }
            else:
                exam = None
        except Exception:
            exam = _get_exam_fallback(session, exam_id)
    else:
        exam = _get_exam_fallback(session, exam_id)

    if not exam:
        return None

    # Sections
    if _domain_available("SectionService"):
        try:
            ssvc = domain_services.get_section_service(session)
            sections = [{
                "id": getattr(s, "id", None),
                "exam_id": getattr(s, "exam_id", None),
                "title": getattr(s, "title", None),
                "order": getattr(s, "order", None),
            } for s in ssvc.list_sections(exam_id)]  # type: ignore[attr-defined]
        except Exception:
            sections = _list_sections_fallback(session, exam_id)
    else:
        sections = _list_sections_fallback(session, exam_id)

    # Questions por sección
    out_sections: List[Dict[str, Any]] = []
    for sec in sections:
        sid = sec.get("id")
        if sid is None:
            continue
        if _domain_available("QuestionService"):
            try:
                qsvc = domain_services.get_question_service(session)
                qlist = qsvc.list_questions(sid)  # type: ignore[attr-defined]
                qs = [_normalize_question({
                    "id": getattr(q, "id", None),
                    "section_id": getattr(q, "section_id", None),
                    "type": getattr(q, "type", None),
                    "stem": getattr(q, "stem", getattr(q, "text", "")),
                    "choices": getattr(q, "choices", None),
                    "answer": getattr(q, "answer", None),
                    "difficulty": getattr(q, "difficulty", None),
                    "tags": getattr(q, "tags", None),
                    "rationale": getattr(q, "rationale", None),
                    "metadata": getattr(q, "metadata", None),
                }) for q in qlist]
            except Exception:
                qs = [_normalize_question(q) for q in _list_questions_fallback(session, sid)]
        else:
            qs = [_normalize_question(q) for q in _list_questions_fallback(session, sid)]

        out_sections.append({**sec, "questions": qs})

    return {"exam": exam, "sections": out_sections}

# ---------- Endpoint ----------

@preview_bp.get("/exams/<int:exam_id>/preview")
def preview(exam_id: int):
    show_solutions = (request.args.get("solutions") or "").lower() in ("1", "true", "yes", "on")
    with get_session() as s:
        tree = _load_exam_tree(s, exam_id)
    if not tree:
        abort(404)

    return render_template(
        "preview.html",
        exam=tree["exam"],
        sections=tree["sections"],
        show_solutions=show_solutions
    )
