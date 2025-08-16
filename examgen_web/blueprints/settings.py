from __future__ import annotations

import os
import platform
from importlib import metadata
from pathlib import Path
from typing import Any, Dict

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from examgen_web.utils import settings_utils as su

bp = Blueprint("settings", __name__)


@bp.get("/")
def index() -> str:
    db_url = os.getenv("EXAMGEN_DB_URL", "sqlite:///./examgen.db")
    db_path = db_url.replace("sqlite:///", "", 1)
    db_info = su.get_db_info(db_path)
    events = su.list_events(50)
    backups = [
        p.name for p in sorted(su.BACKUP_DIR.glob("*.db"), reverse=True)
    ]
    env_info: Dict[str, Any] = {
        "python": platform.python_version(),
        "os": platform.platform(),
    }
    try:
        env_info["examgen"] = metadata.version("examgen")
    except metadata.PackageNotFoundError:
        env_info["examgen"] = "unknown"
    packages = []
    for pkg in ["flask", "sqlalchemy", "jinja2"]:
        try:
            packages.append({"name": pkg, "version": metadata.version(pkg)})
        except metadata.PackageNotFoundError:
            continue
    return render_template(
        "settings/index.html",
        db_info=db_info,
        events=events,
        env_info=env_info,
        packages=packages,
        backups=backups,
    )


@bp.post("/backup")
def backup() -> Any:
    db_url = os.getenv("EXAMGEN_DB_URL", "sqlite:///./examgen.db")
    db_path = db_url.replace("sqlite:///", "", 1)
    dest = Path(su.create_backup(db_path)).resolve()
    su.append_event("backup", {"path": str(dest)})
    return send_from_directory(dest.parent, dest.name, as_attachment=True)


@bp.get("/backups/<path:filename>")
def download_backup(filename: str) -> Any:
    return send_from_directory(
        su.BACKUP_DIR.resolve(), filename, as_attachment=True
    )


@bp.post("/restore")
def restore() -> Any:
    uploaded = request.files.get("db_file")
    if uploaded is None or uploaded.filename == "":
        return redirect(url_for("settings.index"))
    dest = su.save_uploaded_db(uploaded)
    su.append_event("restore", {"path": dest})
    message = (
        f"Archivo restaurado en {dest}. "
        f"Configure EXAMGEN_DB_URL=sqlite:///{dest}"
    )
    return render_template(
        "settings/confirm.html",
        message=message,
        action=url_for("settings.index"),
        method="get",
    )


@bp.post("/clear-history")
def clear_history_route() -> Any:
    su.append_event("history.clear", {})
    su.clear_history()
    return redirect(url_for("settings.index"))


@bp.post("/confirm")
def confirm() -> str:
    action = request.form.get("action")
    message = request.form.get("message", "¿Confirmar?")
    return render_template(
        "settings/confirm.html", action=action, message=message
    )
