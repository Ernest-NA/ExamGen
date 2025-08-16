from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List

from flask import (
    Blueprint,
    Response,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

from examgen.core import models as m
from examgen.core.database import SessionLocal
from examgen_web.utils import import_utils
from examgen_web.utils.audit import append_event

bp = Blueprint("importer", __name__)
LAST_REPORT: Dict[str, Any] | None = None


@bp.get("/")
def upload_form() -> str:
    with SessionLocal() as s:
        has_subjects = s.query(m.Subject).count() > 0
        has_questions = s.query(m.Question).count() > 0
    empty_db = not (has_subjects and has_questions)
    return render_template("import/upload.html", empty_db=empty_db)


@bp.post("/upload")
def upload_file() -> str:
    file = request.files.get("file")
    if file is None or file.filename == "":
        return (
            render_template("import/upload.html", error="Archivo requerido"),
            400,
        )
    content = file.read()
    if len(content) > 10 * 1024 * 1024:
        return (
            render_template("import/upload.html", error="Archivo supera 10MB"),
            400,
        )
    fmt = import_utils.detect_format(file.filename, content[:100])
    headers, preview_rows = import_utils.parse_data(content, fmt, limit=25)
    _, all_rows = import_utils.parse_data(content, fmt, limit=None)
    session["import_data"] = {
        "file_name": file.filename,
        "rows": all_rows,
        "headers": headers,
        "format": fmt,
    }
    return render_template(
        "import/preview.html",
        headers=headers,
        rows=preview_rows,
        fields=import_utils.EXPECTED_FIELDS,
    )


@bp.post("/confirm")
def confirm_import() -> str:
    data = session.get("import_data")
    if not data:
        return redirect(url_for("importer.upload_form"))
    rows = data["rows"]
    headers = data["headers"]
    mapping: Dict[str, str] = {}
    for h in headers:
        field = request.form.get(f"map-{h}")
        if field:
            mapping[h] = field
    selected = [int(idx) for idx in request.form.getlist("row")]
    summary = {
        "file_name": data["file_name"],
        "rows_total": len(selected),
        "imported": 0,
        "duplicates": 0,
        "skipped": 0,
        "rows": [],
    }
    with SessionLocal() as db:
        for idx in selected:
            raw = rows[idx]
            mapped = {mapping[h]: raw.get(h) for h in mapping}
            mapped = import_utils.normalise(mapped)
            subject_name = mapped.get("subject")
            prompt = mapped.get("prompt")
            if not subject_name or not prompt:
                summary["skipped"] += 1
                summary["rows"].append({"row": idx, "status": "skipped"})
                continue
            if import_utils.is_duplicate(db, subject_name, prompt):
                summary["duplicates"] += 1
                summary["rows"].append({"row": idx, "status": "duplicate"})
                continue
            subj = (
                db.query(m.Subject)
                .filter_by(name=subject_name)
                .one_or_none()
            )
            if not subj:
                subj = m.Subject(name=subject_name)
                db.add(subj)
                db.flush()
            question = m.MCQQuestion(
                prompt=prompt,
                explanation=mapped.get("explanation"),
                subject_id=subj.id,
                meta=mapped.get("meta") or {},
            )
            options: List[m.AnswerOption] = []
            correct = str(mapped.get("correct") or "").strip()
            for i in range(1, 6):
                text = mapped.get(f"option_{i}")
                if not text:
                    continue
                is_correct = (
                    correct == str(i) or correct.lower() == text.lower()
                )
                options.append(
                    m.AnswerOption(text=text, is_correct=is_correct)
                )
            if not options:
                summary["skipped"] += 1
                summary["rows"].append({"row": idx, "status": "skipped"})
                continue
            question.options = options
            db.add(question)
            summary["imported"] += 1
            summary["rows"].append({"row": idx, "status": "imported"})
        db.commit()
    global LAST_REPORT
    LAST_REPORT = summary
    append_event(
        "import.completed",
        file_name=summary["file_name"],
        rows_total=summary["rows_total"],
        imported=summary["imported"],
        duplicates=summary["duplicates"],
        skipped=summary["skipped"],
    )
    return render_template("import/result.html", summary=summary)


@bp.get("/report.json")
def report_json() -> Response:
    if LAST_REPORT is None:
        return Response("{}", status=404, mimetype="application/json")
    return Response(
        json.dumps(LAST_REPORT, ensure_ascii=False),
        mimetype="application/json",
    )


@bp.get("/report.csv")
def report_csv() -> Response:
    if LAST_REPORT is None:
        return Response("", status=404, mimetype="text/csv")

    def generate() -> Iterator[str]:
        yield "row,status\n"
        for r in LAST_REPORT["rows"]:
            yield f"{r['row']},{r['status']}\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/csv; charset=utf-8",
    )
