from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, redirect, url_for, abort
from sqlalchemy import text  # type: ignore

from examgen_web.infra.db import get_session
from examgen_web.infra import services as domain_services

sections_bp = Blueprint("sections", __name__)

# ---- Helpers ----

def _domain_available(name: str) -> bool:
    return getattr(domain_services, name, None) is not None


def _section_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(section)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []


def _get_exam_fallback(session, exam_id: int) -> Optional[Dict[str, Any]]:
    try:
        row = session.execute(
            text("SELECT * FROM exam WHERE id = :id"), {"id": exam_id}
        ).mappings().one_or_none()
        return dict(row) if row else None
    except Exception:
        return None


def _insert_section_fallback(
    session, exam_id: int, title: str, order: Optional[int]
) -> Optional[int]:
    cols = set(_section_columns(session))
    if not cols:
        return None
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data: Dict[str, Any] = {"exam_id": exam_id} if "exam_id" in cols else {}
    if "title" in cols:
        data["title"] = title
    if "order" in cols and order is not None:
        data["order"] = order
    if "created_at" in cols:
        data["created_at"] = now
    if "updated_at" in cols:
        data["updated_at"] = now
    if not data:
        return None
    keys = list(data.keys())
    placeholders = [f":{k}" for k in keys]
    session.execute(
        text(
            f"INSERT INTO section ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"
        ),
        data,
    )
    session.commit()
    try:
        rid = session.execute(text("SELECT last_insert_rowid()")).scalar()
        return int(rid) if isinstance(rid, int) else None
    except Exception:
        try:
            rid = session.execute(
                text("SELECT id FROM section ORDER BY id DESC LIMIT 1")
            ).scalar()
            return int(rid) if isinstance(rid, int) else None
        except Exception:
            return None

# ---- Endpoints ----

@sections_bp.get("/exams/<int:exam_id>/sections/new")
def new_section(exam_id: int):
    with get_session() as s:
        exam = _get_exam_fallback(s, exam_id)
    if not exam:
        abort(404)
    return render_template(
        "section_form.html", exam=exam, errors={}, form={"title": "", "order": ""}
    )


@sections_bp.post("/exams/<int:exam_id>/sections")
def create_section(exam_id: int):
    title = (request.form.get("title") or "").strip()
    order_raw = (request.form.get("order") or "").strip()
    order = int(order_raw) if order_raw.isdigit() else None

    errors = {}
    if not title:
        errors["title"] = "El título de la sección es obligatorio."

    if errors:
        return (
            render_template(
                "section_form.html",
                exam={"id": exam_id},
                errors=errors,
                form={"title": title, "order": order_raw},
            ),
            400,
        )

    with get_session() as s:
        if _domain_available("SectionService"):
            try:
                svc = domain_services.get_section_service(s)
                svc.add_section(exam_id, title=title, order=order)  # type: ignore[attr-defined]
            except Exception:
                _insert_section_fallback(s, exam_id, title, order)
        else:
            _insert_section_fallback(s, exam_id, title, order)

    return redirect(url_for("exams.exam_detail", exam_id=exam_id))
