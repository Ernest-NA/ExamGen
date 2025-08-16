from __future__ import annotations

import csv
import io
import json
from typing import Any, List

from sqlalchemy.orm import Session

from examgen.core import models as m

MAX_PREVIEW_ROWS = 25
EXPECTED_FIELDS: List[str] = [
    "subject",
    "prompt",
    "option_1",
    "option_2",
    "option_3",
    "option_4",
    "option_5",
    "correct",
    "explanation",
    "meta",
]


def detect_format(filename: str, snippet: bytes) -> str:
    """Return ``'json'`` or ``'csv'`` based on name or content."""
    name = filename.lower()
    if name.endswith(".json"):
        return "json"
    if name.endswith(".csv"):
        return "csv"
    snippet = snippet.lstrip()
    if snippet.startswith(b"[") or snippet.startswith(b"{"):
        return "json"
    return "csv"


def parse_data(
    data: bytes, fmt: str, limit: int | None = None
) -> tuple[list[str], list[dict[str, Any]]]:
    """Parse bytes ``data`` as CSV/JSON returning headers and rows."""
    if fmt == "json":
        items = json.loads(data.decode("utf-8"))
        if isinstance(items, dict):
            items = [items]
        rows = list(items if limit is None else items[:limit])
        headers = list(rows[0].keys()) if rows else []
        return headers, rows
    # CSV branch
    fh = io.StringIO(data.decode("utf-8"))
    reader = csv.DictReader(fh)
    headers = reader.fieldnames or []
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(reader):
        if limit is not None and i >= limit:
            break
        rows.append(row)
    if limit is None:
        # read remaining rows
        rows.extend(row for row in reader)
    return headers, rows


def normalise(row: dict[str, Any]) -> dict[str, Any]:
    """Trim strings, convert blanks to ``None`` and load meta JSON."""
    clean: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            value = None
        clean[key] = value
    meta = clean.get("meta")
    if isinstance(meta, str):
        try:
            clean["meta"] = json.loads(meta)
        except json.JSONDecodeError:
            clean["meta"] = {}
    return clean


def is_duplicate(session: Session, subject: str, prompt: str) -> bool:
    """Return ``True`` if a question with same subject & prompt exists."""
    subj = session.query(m.Subject).filter_by(name=subject).one_or_none()
    if not subj:
        return False
    return (
        session.query(m.Question)
        .filter_by(subject_id=subj.id, prompt=prompt)
        .first()
        is not None
    )
