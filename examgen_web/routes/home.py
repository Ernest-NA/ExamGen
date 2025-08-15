from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__)


@home_bp.get("/")
def dashboard():
    # En EXG-6.3 agregaremos datos reales (p.e., conteo de exámenes)
    return render_template("dashboard.html")
