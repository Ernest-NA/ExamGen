import json
from pathlib import Path

import pytest

from examgen_web.app import create_app

LOG_PATH = Path("logs/web_events.jsonl")


@pytest.fixture()
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_logs():
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    yield
    if LOG_PATH.exists():
        LOG_PATH.unlink()


def read_events():
    if not LOG_PATH.exists():
        return []
    return [
        json.loads(line)
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines()
    ]


def test_home_view_logs_event(client):
    resp = client.get("/")
    assert resp.status_code == 200
    events = read_events()
    assert any(e.get("event") == "home.viewed" for e in events)


def test_start_redirects_and_logs(client):
    resp = client.get("/start")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/exams")
    events = read_events()
    assert any(e.get("event") == "home.cta_clicked" for e in events)
