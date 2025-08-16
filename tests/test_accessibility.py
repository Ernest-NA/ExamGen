import pytest
from bs4 import BeautifulSoup
from examgen_web.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_base_has_live_region(client):
    resp = client.get("/")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, "html.parser")
    status = soup.select_one("#status[aria-live='polite']")
    assert status is not None


def test_exams_headers_have_scope(client):
    resp = client.get("/exams")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, "html.parser")
    ths = soup.select("table thead th")
    assert ths, "expected table headers"
    for th in ths:
        assert th.get("scope") == "col"
