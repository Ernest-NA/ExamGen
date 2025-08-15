from __future__ import annotations
from typing import Any, Dict, List
import io
import csv
import json
import re

from flask import Blueprint, request, abort, Response, render_template
from sqlalchemy import text  # type: ignore

from examgen_web.infra.db import get_session
from .preview import _load_exam_tree  # reutilizamos la carga normalizada

export_bp = Blueprint("export", __name__)

def _slugify(s: str, fallback: str = "exam") -> str:
    if not s:
        return fallback
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^A-Za-z0-9\-_.]+", "", s)
    return s or fallback

def _bool(v: str | None, default: bool=False) -> bool:
    if v is None:
        return default
    return v.lower() in ("1","true","yes","on")

def _csv_bytes(tree: Dict[str, Any], with_solutions: bool) -> bytes:
    # CSV columnas: section, index, type, stem, choices, answer, difficulty, tags
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["section", "index", "type", "stem", "choices", "answer" if with_solutions else "answer_included=false", "difficulty", "tags"])
    for idx_s, sec in enumerate(tree["sections"], start=1):
        title = sec.get("title") or f"Sección {idx_s}"
        for idx_q, q in enumerate(sec.get("questions", []), start=1):
            choices = "; ".join(q.get("choices") or [])
            tags = "; ".join(q.get("tags") or [])
            answer = q.get("answer") if with_solutions else ""
            w.writerow([title, idx_q, q.get("type") or "", q.get("stem") or "", choices, answer, q.get("difficulty") or "", tags])
    return buf.getvalue().encode("utf-8")

def _json_bytes(tree: Dict[str, Any], with_solutions: bool) -> bytes:
    # Si no se incluyen soluciones, vaciamos el campo 'answer'
    payload = {
        "exam": tree["exam"],
        "sections": []
    }
    for sec in tree["sections"]:
        s_out = {k: sec.get(k) for k in ("id","exam_id","title","order")}
        s_out["questions"] = []
        for q in sec.get("questions", []):
            q_out = {k: q.get(k) for k in ("id","section_id","type","stem","choices","difficulty","tags","rationale","metadata")}
            q_out["answer"] = q.get("answer") if with_solutions else None
            s_out["questions"].append(q_out)
        payload["sections"].append(s_out)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

# ---------- Endpoint ----------

@export_bp.post("/exams/<int:exam_id>/export")
def export_exam(exam_id: int):
    fmt = (request.args.get("fmt") or "").lower()
    if fmt not in ("csv","json","pdf"):
        abort(400, "Parámetro fmt inválido. Use csv|json|pdf.")
    with_solutions = _bool(request.args.get("solutions"), default=False)
    download = _bool(request.args.get("download"), default=True)

    with get_session() as s:
        tree = _load_exam_tree(s, exam_id)
    if not tree:
        abort(404)

    exam_title = tree["exam"].get("title") or f"exam-{exam_id}"
    base = _slugify(exam_title)

    if fmt == "csv":
        body = _csv_bytes(tree, with_solutions)
        resp = Response(body, mimetype="text/csv; charset=utf-8")
        if download:
            resp.headers["Content-Disposition"] = f'attachment; filename="{base}.csv"'
        return resp

    if fmt == "json":
        body = _json_bytes(tree, with_solutions)
        resp = Response(body, mimetype="application/json; charset=utf-8")
        if download:
            resp.headers["Content-Disposition"] = f'attachment; filename="{base}.json"'
        return resp

    # PDF
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        abort(501, "Exportación a PDF requiere 'weasyprint' instalado en local.")

    # Renderizamos HTML con la misma estructura y lo convertimos a PDF
    html_str = render_template("pdf_template.html",
                               exam=tree["exam"],
                               sections=tree["sections"],
                               show_solutions=with_solutions)
    pdf_bytes = HTML(string=html_str, base_url=None).write_pdf()
    resp = Response(pdf_bytes, mimetype="application/pdf")
    if download:
        resp.headers["Content-Disposition"] = f'attachment; filename="{base}.pdf"'
    return resp
