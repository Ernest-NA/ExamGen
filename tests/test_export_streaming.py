import pytest
from examgen_web.app import app as flask_app

@pytest.fixture()
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c

def test_export_fmt_required(client):
    r = client.post("/exams/1/export")
    assert r.status_code in (400, 404)

def test_streaming_headers_when_exists(client):
    # Si el examen no existe, será 404; este test es smoke de ruta.
    r = client.post("/exams/1/export?fmt=json")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert "application/json" in r.headers.get("Content-Type", "")
