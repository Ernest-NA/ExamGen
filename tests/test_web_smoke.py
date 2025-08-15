import json
import pytest
from examgen_web.app import app as flask_app


@pytest.fixture()
def client():
    flask_app.testing = True
    with flask_app.test_client() as c:
        yield c


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data and data.get("status") == "ok"


def test_dashboard_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"ExamGen" in resp.data
