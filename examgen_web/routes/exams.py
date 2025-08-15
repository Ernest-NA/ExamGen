from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, render_template, request, redirect, url_for, abort
from sqlalchemy import text  # type: ignore

from examgen_web.infra.db import get_session
from examgen_web.infra import services as domain_services

exams_bp = Blueprint("exams", __name__)


# ---------- Utilidades ----------

def _domain_available() -> bool:
    # domain_services.ExamService es None si el import falló en EXG-6.2
    return getattr(domain_services, "ExamService", None) is not None


def _to_exam_dict(obj: Any) -> Dict[str, Any]:
    """
    Normaliza entidades de dominio o filas a un dict de vista.
    Se toleran atributos/columnas ausentes.
    """
    get = lambda k, default=None: getattr(obj, k, obj.get(k, default)) if isinstance(obj, dict) else getattr(obj, k, default)
    return {
        "id": get("id"),
        "title": get("title"),
        "description": get("description"),
        "language": get("language"),
        "created_at": get("created_at"),
        "updated_at": get("updated_at"),
    }


# ---- Fallback SQL (sin crear tablas) ----

def _exam_columns(session) -> List[str]:
    cols: List[str] = []
    try:
        res = session.execute(text("PRAGMA table_info(exam)"))
        cols = [row[1] for row in res.fetchall()]  # row[1] = name
    except Exception:
        cols = []
    return cols


def _list_exams_fallback(session) -> List[Dict[str, Any]]:
    cols = _exam_columns(session)
    if not cols:
        return []
    order = "created_at DESC" if "created_at" in cols else "id DESC" if "id" in cols else None
    sql = "SELECT * FROM exam" + (f" ORDER BY {order}" if order else "")
    rows = session.execute(text(sql)).mappings().all()
    return [dict(r) for r in rows]


def _get_exam_fallback(session, exam_id: int) -> Optional[Dict[str, Any]]:
    cols = _exam_columns(session)
    if not cols:
        return None
    row = session.execute(text("SELECT * FROM exam WHERE id = :id"), {"id": exam_id}).mappings().one_or_none()
    return dict(row) if row else None


def _insert_exam_fallback(session, title: str, description: str, language: Optional[str]) -> Optional[int]:
    cols = set(_exam_columns(session))
    if not cols:
        # Tabla inexistente
        return None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data: Dict[str, Any] = {}
    # Solo seteamos columnas existentes para no romper esquema
    if "title" in cols:
        data["title"] = title
    if "description" in cols:
        data["description"] = description
    if "language" in cols:
        data["language"] = language or "es-ES"
    if "created_at" in cols:
        data["created_at"] = now
    if "updated_at" in cols:
        data["updated_at"] = now

    if not data:
        return None

    keys = list(data.keys())
    placeholders = [f":{k}" for k in keys]
    sql = text(f"INSERT INTO exam ({', '.join(keys)}) VALUES ({', '.join(placeholders)})")
    session.execute(sql, data)
    session.commit()

    # Intentar recuperar ID
    if "id" in cols:
        try:
            rid = session.execute(text("SELECT last_insert_rowid()")).scalar()
            if isinstance(rid, int):
                return rid
        except Exception:
            pass
        # Fallback: último por id
        try:
            rid = session.execute(text("SELECT id FROM exam ORDER BY id DESC LIMIT 1")).scalar()
            if isinstance(rid, int):
                return rid
        except Exception:
            pass
    return None


# ---------- Endpoints ----------


@exams_bp.get("/exams")
def list_exams():
    with get_session() as s:
        exams: List[Dict[str, Any]] = []
        if _domain_available():
            try:
                svc = domain_services.get_exam_service(s)
                # Suponemos contratos del dominio: .list_exams() -> lista de entidades
                exams = [_to_exam_dict(e) for e in svc.list_exams()]  # type: ignore[attr-defined]
            except Exception:
                # Si el dominio no tiene esa API, caemos a fallback seguro
                exams = _list_exams_fallback(s)
        else:
            exams = _list_exams_fallback(s)

    return render_template("exams_list.html", exams=exams)


@exams_bp.get("/exams/new")
def new_exam():
    return render_template(
        "exam_form.html",
        errors={},
        form={"title": "", "description": "", "language": "es-ES"},
    )


@exams_bp.post("/exams")
def create_exam():
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    language = (request.form.get("language") or "").strip() or None

    errors: Dict[str, str] = {}
    if not title:
        errors["title"] = "El título es obligatorio."

    if errors:
        return (
            render_template(
                "exam_form.html",
                errors=errors,
                form={
                    "title": title,
                    "description": description,
                    "language": language or "es-ES",
                },
            ),
            400,
        )

    with get_session() as s:
        # Ruta dominio si está disponible
        if _domain_available():
            try:
                svc = domain_services.get_exam_service(s)
                created = svc.create_exam(
                    {
                        "title": title,
                        "description": description,
                        "language": language or "es-ES",
                    }
                )  # type: ignore[attr-defined]
                exam_id = getattr(created, "id", None)
                if exam_id is None:
                    # Si el dominio no devuelve ID, consultamos el último examen
                    # (esto no crea tablas ni cambia esquema)
                    rows = _list_exams_fallback(s)
                    exam_id = rows[0]["id"] if rows and "id" in rows[0] else None
            except Exception:
                # Fallback seguro
                exam_id = _insert_exam_fallback(s, title, description, language)
        else:
            exam_id = _insert_exam_fallback(s, title, description, language)

    if isinstance(exam_id, int):
        return redirect(url_for("exams.exam_detail", exam_id=exam_id))
    # Si no hay ID disponible, volvemos al listado
    return redirect(url_for("exams.list_exams"))


@exams_bp.get("/exams/<int:exam_id>")
def exam_detail(exam_id: int):
    with get_session() as s:
        exam: Optional[Dict[str, Any]] = None
        if _domain_available():
            try:
                svc = domain_services.get_exam_service(s)
                e = svc.get_exam(exam_id)  # type: ignore[attr-defined]
                if e:
                    exam = _to_exam_dict(e)
            except Exception:
                exam = _get_exam_fallback(s, exam_id)
        else:
            exam = _get_exam_fallback(s, exam_id)

    if not exam:
        abort(404)
    # Nota: Secciones y preguntas llegarán en EXG-6.4
    return render_template("exam_detail.html", exam=exam)
