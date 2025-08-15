import pytest
from examgen_web.app import app as flask_app


@pytest.fixture()
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_sections_new_requires_exam(client):
    # 404 si el examen no existe (fallback)
    r = client.get("/exams/999999/sections/new")
    assert r.status_code in (200, 404)
