from __future__ import annotations
from typing import Any, Dict, List
import io
import csv
import json
import re

from flask import Blueprint, request, abort, Response, render_template, stream_with_context

from examgen_web.infra.db import get_session
from .preview import _load_exam_tree  # reutilizamos normalización del árbol

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

# ------------------ STREAMING HELPERS ------------------

def _csv_stream(tree: Dict[str, Any], with_solutions: bool):
    """
    Genera CSV línea a línea usando csv.writer sobre un buffer pequeño por fila.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    # Cabecera
    w.writerow(["section", "index", "type", "stem", "choices", "answer" if with_solutions else "answer_included=false", "difficulty", "tags"])
    yield buf.getvalue()
    buf.seek(0); buf.truncate(0)

    for idx_s, sec in enumerate(tree["sections"], start=1):
        title = sec.get("title") or f"Sección {idx_s}"
        for idx_q, q in enumerate(sec.get("questions", []), start=1):
            choices = "; ".join(q.get("choices") or [])
            tags = "; ".join(q.get("tags") or [])
            answer = q.get("answer") if with_solutions else ""
            w.writerow([title, idx_q, q.get("type") or "", q.get("stem") or "", choices, answer, q.get("difficulty") or "", tags])
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

def _json_stream(tree: Dict[str, Any], with_solutions: bool):
    """
    Emite JSON válido por partes: { "exam": {...}, "sections": [ { ... "questions": [ {...}, ... ] }, ... ] }
    """
    # Encabezado + exam
    yield "{\n  \"exam\": "
    yield json.dumps(tree["exam"], ensure_ascii=False)
    yield ",\n  \"sections\": ["

    for i, sec in enumerate(tree["sections"]):
        if i > 0:
            yield ","
        # Abrir sección
        s_out = {k: sec.get(k) for k in ("id","exam_id","title","order")}
        yield "\n    {"
        yield "\"id\": " + json.dumps(s_out.get("id"), ensure_ascii=False)
        yield ", \"exam_id\": " + json.dumps(s_out.get("exam_id"), ensure_ascii=False)
        yield ", \"title\": " + json.dumps(s_out.get("title"), ensure_ascii=False)
        yield ", \"order\": " + json.dumps(s_out.get("order"), ensure_ascii=False)
        yield ", \"questions\": ["

        qs = sec.get("questions", [])
        for j, q in enumerate(qs):
            if j > 0:
                yield ","
            q_out = {k: q.get(k) for k in ("id","section_id","type","stem","choices","difficulty","tags","rationale","metadata")}
            if not with_solutions:
                q_out["answer"] = None
            else:
                q_out["answer"] = q.get("answer")
            yield "\n      " + json.dumps(q_out, ensure_ascii=False)

        # Cerrar sección
        yield "\n    ]}"  # end questions + section

    # Cerrar documento
    yield "\n  ]\n}\n"

# ------------------ ROUTE ------------------

@export_bp.post("/exams/<int:exam_id>/export")
def export_exam(exam_id: int):
    fmt = (request.args.get("fmt") or "").lower()
    if fmt not in ("csv","json","pdf"):
        abort(400, "Parámetro fmt inválido. Use csv|json|pdf.")
    with_solutions = _bool(request.args.get("solutions"), default=False)
    download = _bool(request.args.get("download"), default=True)

    # Cargamos el árbol normalizado (puede ocupar memoria si el examen es enorme);
    # el streaming evita construir un único buffer de salida gigante.
    with get_session() as s:
        tree = _load_exam_tree(s, exam_id)
    if not tree:
        abort(404)

    exam_title = tree["exam"].get("title") or f"exam-{exam_id}"
    base = _slugify(exam_title)

    if fmt == "csv":
        gen = _csv_stream(tree, with_solutions)
        resp = Response(stream_with_context(gen), mimetype="text/csv; charset=utf-8")
        if download:
            resp.headers["Content-Disposition"] = f'attachment; filename="{base}.csv"'
        return resp

    if fmt == "json":
        gen = _json_stream(tree, with_solutions)
        resp = Response(stream_with_context(gen), mimetype="application/json; charset=utf-8")
        if download:
            resp.headers["Content-Disposition"] = f'attachment; filename="{base}.json"'
        return resp

    # PDF (no streaming por ahora; se mantiene comportamiento de EXG-6.5)
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        abort(501, "Exportación a PDF requiere 'weasyprint' instalado en local.")

    html_str = render_template("pdf_template.html",
                               exam=tree["exam"],
                               sections=tree["sections"],
                               show_solutions=with_solutions)
    pdf_bytes = HTML(string=html_str, base_url=None).write_pdf()
    resp = Response(pdf_bytes, mimetype="application/pdf")
    if download:
        resp.headers["Content-Disposition"] = f'attachment; filename="{base}.pdf"'
    return resp
