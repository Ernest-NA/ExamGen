from __future__ import annotations

from typing import Dict

from flask import Blueprint, Response, redirect, render_template

from ..utils.audit import append_event
from .exams import list_exams
from .attempts import list_attempts

bp = Blueprint("main", __name__)


@bp.get("/")
def index() -> str:
    counts: Dict[str, int | None] = {}
    try:
        counts["exams"] = len(list_exams())
    except Exception:
        counts["exams"] = None
    try:
        counts["attempts"] = len(list_attempts())
    except Exception:
        counts["attempts"] = None
    append_event("home.viewed")
    return render_template("home/index.html", counts=counts)


@bp.get("/start")
def start() -> Response:
    append_event("home.cta_clicked")
    return redirect("/exams")
