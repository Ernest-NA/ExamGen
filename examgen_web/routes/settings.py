from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from examgen_web.infra.config import get_db_url
from examgen_web.infra.history import _events_path

settings_bp = Blueprint("settings", __name__)


@settings_bp.get("/settings")
def view_settings():
    db_url = get_db_url()
    db_info = {
        "url": db_url,
        "exists": False,
        "size": None,
        "mtime": None,
    }
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", "", 1))
        if db_path.exists():
            stat = db_path.stat()
            db_info.update(
                exists=True,
                size=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
            )
    pdf_ok = False
    try:
        import weasyprint  # type: ignore  # noqa: F401

        pdf_ok = True
    except Exception:
        pdf_ok = False

    hist_path = _events_path()
    hist_info = {
        "path": hist_path,
        "exists": hist_path.exists(),
        "size": hist_path.stat().st_size if hist_path.exists() else 0,
        "events": [],
    }
    if hist_info["exists"]:
        with hist_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-10:]
        for line in lines:
            try:
                hist_info["events"].append(json.loads(line))
            except Exception:
                continue

    return render_template(
        "settings.html",
        db=db_info,
        pdf_ok=pdf_ok,
        history=hist_info,
    )


@settings_bp.post("/settings/backup")
def backup_db():
    db_url = get_db_url()
    if not db_url.startswith("sqlite:///"):
        flash("Solo soportado para SQLite", "error")
        return redirect(url_for("settings.view_settings"))
    db_path = Path(db_url.replace("sqlite:///", "", 1))
    if not db_path.exists():
        flash("BD no encontrada", "error")
        return redirect(url_for("settings.view_settings"))
    backup_dir = Path(__file__).resolve().parents[1] / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    out = backup_dir / f"examgen-{ts}.db"
    shutil.copy2(db_path, out)
    flash(f"Backup creado en {out}", "success")
    return redirect(url_for("settings.view_settings"))


@settings_bp.post("/settings/history/clear")
def clear_history():
    path = _events_path()
    if path.exists():
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        path.rename(path.with_name(f"events-{ts}.jsonl"))
    path.touch(exist_ok=True)
    flash("Historial limpiado", "success")
    return redirect(url_for("settings.view_settings"))


@settings_bp.post("/settings/restore")
def restore_db():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Archivo requerido", "error")
        return redirect(url_for("settings.view_settings"))
    dest_dir = Path.home() / ".examgen" / "databases"
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    dest = dest_dir / f"restore-{ts}.db"
    file.save(dest)
    new_url = f"sqlite:///{dest.as_posix()}"
    flash(
        "BD restaurada. Reinicia la app y establece EXAMGEN_DB_URL=" + new_url,
        "success",
    )
    return redirect(url_for("settings.view_settings"))
