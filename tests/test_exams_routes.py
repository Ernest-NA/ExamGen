import pytest
from examgen_web.app import app as flask_app


@pytest.fixture()
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_exams_list_ok(client):
    r = client.get("/exams")
    assert r.status_code == 200


def test_new_exam_form_ok(client):
    r = client.get("/exams/new")
    assert r.status_code == 200
