from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, Iterable, List

from flask import Blueprint, Response, current_app, render_template, stream_with_context

bp = Blueprint("exams", __name__)


# --- Helpers: dominio primero; si falla, fallback SQL ---
def _db_path_from_url(url: str) -> str:
    # soporta sqlite:///./examgen.db y rutas absolutas/relativas
    if not url or not url.startswith("sqlite"):
        return "./examgen.db"
    path = url.split("///", 1)[-1]
    return path


def _detect_exams_table(conn: sqlite3.Connection) -> Dict[str, Any] | None:
    # heurística: buscar tabla con columnas típicas
    candidates: List[Dict[str, Any]] = []
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for (tname,) in tables:
        cols = conn.execute(f"PRAGMA table_info('{tname}')").fetchall()
        colnames = {c[1].lower() for c in cols}
        if {"id"} <= colnames and ({"title"} <= colnames or {"name"} <= colnames):
            score = 0
            for k in ("created_at", "created", "inserted_at"):
                if k in colnames:
                    score += 1
            candidates.append({"name": tname, "cols": colnames, "score": score})
    if not candidates:
        return None
    # priorizar por score y nombre amistoso
    candidates.sort(key=lambda c: (c["score"], "exam" in c["name"].lower()), reverse=True)
    return candidates[0]


def _list_exams_fallback(limit: int = 50) -> List[Dict[str, Any]]:
    url = os.getenv("EXAMGEN_DB_URL", "sqlite:///./examgen.db")
    path = _db_path_from_url(url)
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        meta = _detect_exams_table(conn)
        if not meta:
            return []
        t = meta["name"]
        # columnas habituales; seleccionar lo disponible
        cols_pref = [
            "id",
            "title",
            "name",
            "created_at",
            "created",
            "updated_at",
            "updated",
        ]
        cols = [c for c in cols_pref if c in meta["cols"]]
        if not cols:
            return []
        sql = f"SELECT {', '.join(cols)} FROM {t} ORDER BY 1 DESC LIMIT ?"
        rows = conn.execute(sql, (limit,)).fetchall()
        data: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d.setdefault("title", d.get("name"))
            data.append({"id": d.get("id"), "title": d.get("title"), "raw": d})
        return data
    finally:
        conn.close()


def list_exams(limit: int = 50) -> List[Dict[str, Any]]:
    # Dominio primero (si existiese un servicio expuesto)
    try:
        # Ejemplo: from src.examgen.services import list_exams as _svc
        # return _svc(limit=limit)
        raise ImportError  # fuerza fallback si no hay servicio
    except Exception:
        return _list_exams_fallback(limit=limit)


# --- Rutas ---
@bp.get("/")
def exams_index() -> str:
    items = list_exams()
    return render_template("exams/list.html", items=items)


def _stream_json(items: Iterable[Dict[str, Any]]) -> Iterable[str]:
    yield "["
    first = True
    for it in items:
        if not first:
            yield ","
        yield json.dumps(it["raw"], ensure_ascii=False)
        first = False
    yield "]"


@bp.get("/exams.json")
def export_json() -> Response:
    items = list_exams(limit=10000)
    return Response(
        stream_with_context(_stream_json(items)),
        mimetype="application/json",
    )


def _stream_csv(items: Iterable[Dict[str, Any]]) -> Iterable[str]:
    # encabezados dinámicos de la primera fila
    it = list(items)
    if not it:
        yield ""
        return
    headers = list(it[0]["raw"].keys())
    yield ",".join(headers) + "\n"
    for row in it:
        vals = [str(row["raw"].get(h, "")) for h in headers]
        yield ",".join(vals) + "\n"


@bp.get("/exams.csv")
def export_csv() -> Response:
    items = list_exams(limit=10000)
    return Response(
        stream_with_context(_stream_csv(items)),
        mimetype="text/csv; charset=utf-8",
    )
