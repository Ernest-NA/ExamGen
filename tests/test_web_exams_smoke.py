import pytest
from examgen_web.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_list_exams(client):
    resp = client.get("/exams")
    assert resp.status_code == 200


def test_export_json(client):
    resp = client.get("/exams/exams.json")
    assert resp.status_code == 200
    assert resp.mimetype.startswith("application/json")


def test_export_csv(client):
    resp = client.get("/exams/exams.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.mimetype
