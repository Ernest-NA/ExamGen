from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "app": "ExamGen Web",
        "version": "0.1.0",
        "mode": "local"
    }), 200
