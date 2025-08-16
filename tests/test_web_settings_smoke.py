from pathlib import Path

import pytest

from examgen_web.app import create_app
from examgen_web.utils.settings_utils import LOG_PATH, append_event


@pytest.fixture()
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_settings_page(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Estado de la BD" in body
    assert "Historial de eventos" in body


def test_backup_endpoint(client):
    db_path = Path("examgen.db")
    if not db_path.exists():
        import sqlite3

        sqlite3.connect(db_path).close()
    size = db_path.stat().st_size
    resp = client.post("/settings/backup")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Disposition", "").endswith(".db")
    assert len(resp.data) == size


def test_clear_history(client):
    if LOG_PATH.exists():
        LOG_PATH.unlink()
    append_event("test", {})
    assert LOG_PATH.exists()
    client.post("/settings/clear-history")
    assert not LOG_PATH.exists()
