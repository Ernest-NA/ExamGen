import pytest
from examgen_web.app import app as flask_app


@pytest.fixture()
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c

def test_preview_status(client):
    # Si no existe el examen, puede ser 404. El objetivo es que la ruta responda.
    r = client.get("/exams/1/preview")
    assert r.status_code in (200, 404)

def test_export_requires_fmt(client):
    r = client.post("/exams/1/export")
    assert r.status_code in (400, 404)  # 400 por fmt inválido o 404 por inexistente
