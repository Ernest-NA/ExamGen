import pytest
from examgen_web.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_take_exam_flow(client):
    resp = client.get("/exams/1/take")
    assert resp.status_code == 200
    resp = client.post("/exams/1/take", data={"answer": "A", "idx": 0}, follow_redirects=False)
    assert resp.status_code == 302
    attempt_url = resp.headers["Location"]
    resp = client.get(attempt_url)
    assert resp.status_code == 200
    resp = client.get(f"{attempt_url}.json")
    assert resp.status_code == 200
    assert resp.mimetype.startswith("application/json")
    resp = client.get(f"{attempt_url}.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.mimetype
