from flask import Flask
from .blueprints.exams import bp as exams_bp
from .blueprints.attempts import bp as attempts_bp
from .blueprints.player import bp as player_bp
from .blueprints.importer import bp as importer_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = "dev"
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    # Navegación sin barra final y registro de blueprints
    app.url_map.strict_slashes = False
    app.register_blueprint(exams_bp, url_prefix="/exams")
    app.register_blueprint(attempts_bp, url_prefix="/attempts")
    app.register_blueprint(player_bp)
    app.register_blueprint(importer_bp, url_prefix="/import")
    return app
