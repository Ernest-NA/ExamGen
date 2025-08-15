from flask import Flask, request
from .routes.home import home_bp
from .routes.health import health_bp
from .routes.exams import exams_bp
from .routes.sections import sections_bp
from .routes.questions import questions_bp
from .routes.preview import preview_bp      # <- NUEVO
from .routes.export import export_bp        # <- NUEVO
from .routes.importer import importer_bp    # <- NUEVO
from .routes.settings import settings_bp    # <- NUEVO

APP_VERSION = "0.1.0"


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    app.secret_key = "examgen-secret"
    # Blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(sections_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(preview_bp)      # <- NUEVO
    app.register_blueprint(export_bp)       # <- NUEVO
    app.register_blueprint(importer_bp)     # <- NUEVO
    app.register_blueprint(settings_bp)     # <- NUEVO

    @app.context_processor
    def inject_globals():
        endpoint = request.endpoint or ""
        nav = ""
        if endpoint.startswith("home."):
            nav = "home"
        elif endpoint.startswith("exams."):
            nav = "exams"
        return {"nav_active": nav, "app_version": APP_VERSION}

    return app
