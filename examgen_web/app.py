from flask import Flask
from .blueprints.exams import bp as exams_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    # Navegación sin barra final y registro del blueprint de exámenes
    app.url_map.strict_slashes = False
    app.register_blueprint(exams_bp, url_prefix="/exams")
    return app
