from flask import Flask
from .routes.home import home_bp
from .routes.health import health_bp
from .routes.exams import exams_bp
from .routes.sections import sections_bp
from .routes.questions import questions_bp
from .routes.preview import preview_bp      # <- NUEVO
from .routes.export import export_bp        # <- NUEVO


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    # Blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(sections_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(preview_bp)      # <- NUEVO
    app.register_blueprint(export_bp)       # <- NUEVO
    return app
