from flask import Blueprint, jsonify
from examgen_web.infra.config import load_settings, db_file_exists
from examgen_web.infra import db as dbi

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    settings = load_settings()
    exists = db_file_exists(settings.db_url)
    db_probe = {"status": "missing"} if not exists else dbi.ping()

    return (
        jsonify(
            {
                "status": "ok",
                "app": "ExamGen Web",
                "version": "0.1.0",
                "mode": "local",
                "db": {"url": settings.db_url, "exists": exists, **db_probe},
            }
        ),
        200,
    )
