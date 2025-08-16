from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, Iterable, List

from flask import (
    Blueprint,
    Response,
    render_template,
    request,
    stream_with_context,
)

from ..utils.audit import append_event

bp = Blueprint("attempts", __name__)


# --- Helpers ---

def _db_path_from_url(url: str) -> str:
    if not url or not url.startswith("sqlite"):
        return "./examgen.db"
    return url.split("///", 1)[-1]


def _detect_attempts_table(conn: sqlite3.Connection) -> Dict[str, Any] | None:
    candidates = [
        "attempts",
        "exam_attempts",
        "results",
        "submissions",
        "exam_results",
    ]
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    matches: List[Dict[str, Any]] = []
    for (tname,) in tables:
        if tname.lower() not in candidates:
            continue
        cols = conn.execute(f"PRAGMA table_info('{tname}')").fetchall()
        colnames = {c[1].lower() for c in cols}
        score = 0
        for c in ("id", "exam_id", "score", "status"):
            if c in colnames:
                score += 1
        for c in (
            "started_at",
            "started",
            "start_time",
            "created_at",
            "created",
        ):
            if c in colnames:
                score += 1
        for c in (
            "submitted_at",
            "finished_at",
            "completed_at",
            "end_time",
            "updated_at",
            "updated",
        ):
            if c in colnames:
                score += 1
        matches.append({"name": tname, "cols": colnames, "score": score})
    if not matches:
        return None
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[0]


def _detect_exams_table(conn: sqlite3.Connection) -> Dict[str, Any] | None:
    for tname in ("exams", "exam", "exam_bank"):
        cols = conn.execute(f"PRAGMA table_info('{tname}')").fetchall()
        if not cols:
            continue
        colnames = {c[1].lower() for c in cols}
        if "id" in colnames and ("title" in colnames or "name" in colnames):
            return {"name": tname, "cols": colnames}
    return None


def _list_attempts_fallback(
    exam_id: int | None = None, limit: int = 200
) -> List[Dict[str, Any]]:
    url = os.getenv("EXAMGEN_DB_URL", "sqlite:///./examgen.db")
    path = _db_path_from_url(url)
    if not os.path.exists(path):
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        meta = _detect_attempts_table(conn)
        if not meta:
            return []
        t = meta["name"]
        cols = meta["cols"]
        select_cols: List[str] = []
        if "id" in cols:
            select_cols.append(f"{t}.id AS attempt_id")
        if "exam_id" in cols:
            select_cols.append(f"{t}.exam_id AS exam_id")
        start_col = next(
            (
                c
                for c in (
                    "started_at",
                    "started",
                    "start_time",
                    "created_at",
                    "created",
                )
                if c in cols
            ),
            None,
        )
        if start_col:
            select_cols.append(f"{t}.{start_col} AS started_at")
        end_col = next(
            (
                c
                for c in (
                    "submitted_at",
                    "finished_at",
                    "completed_at",
                    "end_time",
                    "updated_at",
                    "updated",
                )
                if c in cols
            ),
            None,
        )
        if end_col:
            select_cols.append(f"{t}.{end_col} AS submitted_at")
        if "score" in cols:
            select_cols.append(f"{t}.score AS score")
        if "status" in cols:
            select_cols.append(f"{t}.status AS status")
        join = ""
        exams_meta = _detect_exams_table(conn)
        if exams_meta and "exam_id" in cols:
            et = exams_meta["name"]
            ecols = exams_meta["cols"]
            title_col = "title" if "title" in ecols else "name"
            select_cols.append(f"{et}.{title_col} AS exam_title")
            join = f" LEFT JOIN {et} ON {t}.exam_id = {et}.id"
        if not select_cols:
            return []
        sql = f"SELECT {', '.join(select_cols)} FROM {t}{join}"
        params: List[Any] = []
        where: List[str] = []
        if exam_id is not None and "exam_id" in cols:
            where.append(f"{t}.exam_id = ?")
            params.append(exam_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        order_col = "started_at" if start_col else None
        if order_col is None and end_col:
            order_col = "submitted_at"
        if order_col:
            sql += f" ORDER BY {order_col} DESC"
        elif "id" in cols:
            sql += f" ORDER BY {t}.id DESC"
        sql += " LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        data: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            data.append(
                {
                    "attempt_id": d.get("attempt_id"),
                    "exam_id": d.get("exam_id"),
                    "exam_title": d.get("exam_title"),
                    "started_at": d.get("started_at"),
                    "submitted_at": d.get("submitted_at"),
                    "score": d.get("score"),
                    "status": d.get("status"),
                    "raw": d,
                }
            )
        return data
    finally:
        conn.close()


def list_attempts(
    exam_id: int | None = None, limit: int = 200
) -> List[Dict[str, Any]]:
    try:
        from src.examgen.core.services import exam_service  # type: ignore

        return exam_service.list_attempts(exam_id=exam_id, limit=limit)
    except Exception:
        return _list_attempts_fallback(exam_id=exam_id, limit=limit)


# --- Routes ---

@bp.get("/")
def attempts_index() -> str:
    exam_id = request.args.get("exam_id", type=int)
    items = list_attempts(exam_id=exam_id)
    append_event(
        "attempts.viewed",
        route=request.path,
        exam_id=exam_id,
        count=len(items),
    )
    return render_template("attempts/list.html", items=items, exam_id=exam_id)


def _stream_json(items: Iterable[Dict[str, Any]]) -> Iterable[str]:
    yield "["
    first = True
    for it in items:
        if not first:
            yield ","
        yield json.dumps(it["raw"], ensure_ascii=False)
        first = False
    yield "]"


@bp.get("/attempts.json")
def export_json() -> Response:
    exam_id = request.args.get("exam_id", type=int)
    items = list_attempts(exam_id=exam_id, limit=10000)
    append_event(
        "attempts.exported",
        route=request.path,
        exam_id=exam_id,
        count=len(items),
    )
    return Response(
        stream_with_context(_stream_json(items)),
        mimetype="application/json",
    )


def _stream_csv(items: Iterable[Dict[str, Any]]) -> Iterable[str]:
    it = list(items)
    if not it:
        yield ""
        return
    headers = list(it[0]["raw"].keys())
    yield ",".join(headers) + "\n"
    for row in it:
        vals = [str(row["raw"].get(h, "")) for h in headers]
        yield ",".join(vals) + "\n"


@bp.get("/attempts.csv")
def export_csv() -> Response:
    exam_id = request.args.get("exam_id", type=int)
    items = list_attempts(exam_id=exam_id, limit=10000)
    append_event(
        "attempts.exported",
        route=request.path,
        exam_id=exam_id,
        count=len(items),
    )
    return Response(
        stream_with_context(_stream_csv(items)),
        mimetype="text/csv; charset=utf-8",
    )
