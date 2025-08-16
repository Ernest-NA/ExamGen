from flask import Flask, g, redirect, request
from .blueprints.exams import bp as exams_bp
from .blueprints.attempts import bp as attempts_bp
from .blueprints.player import bp as player_bp
from .blueprints.settings import bp as settings_bp
from .blueprints.clone import bp as questions_bp
from .utils.i18n import (
    get_locale,
    set_language as set_language_pref,
    translate,
)

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
    app.jinja_env.globals.update(
        _=lambda s: translate(s, getattr(g, "lang", "es"))
    )

    @app.before_request
    def _determine_lang() -> None:  # pragma: no cover - simple setter
        g.lang = get_locale(request)

    @app.post("/set-language")
    def set_language():  # pragma: no cover - simple redirect
        lang = request.form.get("lang", "es")
        set_language_pref(lang)
        resp = redirect(request.referrer or "/")
        resp.set_cookie("lang", lang, max_age=31536000)
        return resp

    return app
