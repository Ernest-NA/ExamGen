from flask import Flask
from .blueprints.exams import bp as exams_bp
from .blueprints.attempts import bp as attempts_bp
from .blueprints.player import bp as player_bp
from .blueprints.settings import bp as settings_bp
from .blueprints.clone import bp as questions_bp

try:  # Importer blueprint may depend on optional packages
    from .blueprints.importer import bp as importer_bp
except Exception:  # pragma: no cover - optional
    importer_bp = None


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = "dev"
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    # Navegación sin barra final y registro de blueprints
    app.url_map.strict_slashes = False
    app.register_blueprint(exams_bp, url_prefix="/exams")
    app.register_blueprint(attempts_bp, url_prefix="/attempts")
    app.register_blueprint(player_bp)
    app.register_blueprint(questions_bp)
    if importer_bp is not None:
        app.register_blueprint(importer_bp, url_prefix="/import")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    return app
