from examgen_web.app import app as flask_app


def test_health_db_keys():
    flask_app.testing = True
    with flask_app.test_client() as c:
        r = c.get("/health")
        assert r.status_code == 200
        data = r.get_json()
        assert "db" in data
        assert "url" in data["db"]
        assert "exists" in data["db"]
        assert "status" in data["db"]
