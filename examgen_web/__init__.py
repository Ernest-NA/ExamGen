from flask import Flask
from .routes.home import home_bp
from .routes.health import health_bp
from .routes.exams import exams_bp
from .routes.sections import sections_bp      # <- NUEVO
from .routes.questions import questions_bp    # <- NUEVO


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
    app.register_blueprint(sections_bp)       # <- NUEVO
    app.register_blueprint(questions_bp)      # <- NUEVO
    return app
