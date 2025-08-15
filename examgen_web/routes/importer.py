from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import text

from examgen_web.infra.db import get_session
from examgen_web.infra import history
from examgen_web.infra.fileio import TMP_DIR, UploadError, cleanup, save_upload

importer_bp = Blueprint("importer", __name__)

ALLOWED_EXT = {".json", ".csv"}


@importer_bp.get("/import")
def import_step1():
    return render_template("import_step1.html")


def _parse_json(path: Path) -> Dict[str, any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    exam = data.get("exam", {})
    sections = data.get("sections", [])
    qcount = sum(len(sec.get("questions", [])) for sec in sections)
    sample: List[dict] = []
    for sec in sections:
        sample.extend(sec.get("questions", [])[:5])
        if len(sample) >= 5:
            break
    return {
        "exam": exam,
        "sections": sections,
        "question_count": qcount,
        "sample": sample[:5],
    }


def _parse_csv(path: Path) -> Dict[str, any]:
    with path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {
        "exam": {},
        "sections": [],
        "question_count": len(rows),
        "sample": rows[:5],
        "rows": rows,
    }


@importer_bp.post("/import/preview")
def import_preview():
    file = request.files.get("file")
    mode = request.form.get("mode") or "new"
    fmt = request.form.get("fmt") or ""
    if not file or not file.filename:
        flash("Archivo requerido", "error")
        return redirect(url_for("importer.import_step1"))
    try:
        path = save_upload(file, allowed_extensions=ALLOWED_EXT)
    except UploadError as e:
        flash(str(e), "error")
        return redirect(url_for("importer.import_step1"))

    fmt = fmt or path.suffix.lstrip(".")
    try:
        if fmt == "json":
            parsed = _parse_json(path)
        elif fmt == "csv":
            parsed = _parse_csv(path)
        else:
            raise ValueError("Formato no soportado")
    except Exception as exc:  # noqa: BLE001
        cleanup(path)
        flash(f"Error al parsear: {exc}", "error")
        return redirect(url_for("importer.import_step1"))

    token = path.name
    session["import_token"] = token
    session["import_format"] = fmt
    return render_template(
        "import_step2_preview.html",
        mode=mode,
        fmt=fmt,
        token=token,
        data=parsed,
    )


def _exam_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(exam)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []


def _section_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(section)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []


def _question_columns(session) -> List[str]:
    try:
        res = session.execute(text("PRAGMA table_info(question)"))
        return [row[1] for row in res.fetchall()]
    except Exception:
        return []


@importer_bp.post("/import/commit")
def import_commit():
    token = session.get("import_token")
    fmt = session.get("import_format")
    mode = request.form.get("mode") or "new"
    if not token or not fmt:
        flash("Sesión de importación no encontrada", "error")
        return redirect(url_for("importer.import_step1"))
    path = TMP_DIR / token
    if not path.exists():
        flash("Archivo temporal no encontrado", "error")
        return redirect(url_for("importer.import_step1"))

    try:
        if fmt == "json":
            parsed = _parse_json(path)
        else:
            parsed = _parse_csv(path)
    except Exception as exc:  # noqa: BLE001
        cleanup(path)
        flash(f"Error al parsear: {exc}", "error")
        return redirect(url_for("importer.import_step1"))

    counts = {
        "sections": len(parsed.get("sections", [])),
        "questions": parsed.get("question_count", 0),
    }

    with get_session() as s:
        exam_id = None
        cols = _exam_columns(s)
        if mode == "new" and cols:
            title = parsed.get("exam", {}).get("title", "Imported Exam")
            data = {"title": title}
            if "created_at" in cols:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                data.setdefault("created_at", now)
                data.setdefault("updated_at", now)
            keys = list(data.keys())
            placeholders = ", ".join(f":{k}" for k in keys)
            s.execute(text(f"INSERT INTO exam ({', '.join(keys)}) VALUES ({placeholders})"), data)
            s.commit()
            exam_id = s.execute(text("SELECT last_insert_rowid()")).scalar()
            history.record_event(
                exam_id=exam_id if isinstance(exam_id, int) else None,
                entity="exam",
                action="import_create",
                entity_id=exam_id if isinstance(exam_id, int) else None,
                summary=title,
                before=None,
                after=data,
                extra=None,
            )
            # Sections
            sec_cols = _section_columns(s)
            q_cols = _question_columns(s)
            for order, sec in enumerate(parsed.get("sections", []), start=1):
                sec_data = {"exam_id": exam_id, "title": sec.get("title", f"Section {order}")}
                if "order" in sec_cols:
                    sec_data["order"] = order
                keys = list(sec_data.keys())
                placeholders = ", ".join(f":{k}" for k in keys)
                s.execute(text(f"INSERT INTO section ({', '.join(keys)}) VALUES ({placeholders})"), sec_data)
                sec_id = s.execute(text("SELECT last_insert_rowid()")).scalar()
                history.record_event(
                    exam_id=exam_id if isinstance(exam_id, int) else None,
                    entity="section",
                    action="import_create",
                    entity_id=sec_id if isinstance(sec_id, int) else None,
                    summary=sec_data.get("title"),
                    before=None,
                    after=sec_data,
                    extra=None,
                )
                for q in sec.get("questions", []):
                    q_data = {"section_id": sec_id, "stem": q.get("stem") or q.get("prompt")}
                    if "type" in q_cols:
                        q_data["type"] = q.get("type")
                    if "choices" in q_cols:
                        choices = q.get("choices")
                        if isinstance(choices, list):
                            q_data["choices"] = json.dumps(choices, ensure_ascii=False)
                        elif isinstance(choices, str):
                            q_data["choices"] = choices
                    if "answer" in q_cols:
                        q_data["answer"] = q.get("answer")
                    if "difficulty" in q_cols and q.get("difficulty") is not None:
                        q_data["difficulty"] = q.get("difficulty")
                    if "tags" in q_cols:
                        tags = q.get("tags")
                        if isinstance(tags, list):
                            q_data["tags"] = json.dumps(tags, ensure_ascii=False)
                        elif isinstance(tags, str):
                            q_data["tags"] = tags
                    keys = list(q_data.keys())
                    placeholders = ", ".join(f":{k}" for k in keys)
                    s.execute(text(f"INSERT INTO question ({', '.join(keys)}) VALUES ({placeholders})"), q_data)
                    q_id = s.execute(text("SELECT last_insert_rowid()")).scalar()
                    history.record_event(
                        exam_id=exam_id if isinstance(exam_id, int) else None,
                        entity="question",
                        action="import_create",
                        entity_id=q_id if isinstance(q_id, int) else None,
                        summary=q_data.get("stem"),
                        before=None,
                        after=q_data,
                        extra=None,
                    )
            s.commit()

        history.record_event(
            exam_id=exam_id if isinstance(exam_id, int) else None,
            entity="import",
            action="commit",
            entity_id=exam_id if isinstance(exam_id, int) else None,
            summary="Import",  # type: ignore[arg-type]
            before=None,
            after=None,
            extra={"counts": counts},
        )

    cleanup(path)
    session.pop("import_token", None)
    session.pop("import_format", None)
    return render_template("import_step3_result.html", counts=counts, exam_id=exam_id)
