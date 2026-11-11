"""Служебные адреса, глобальная обработка ошибок, раздача интерфейса (ТЗ 4.3a, 7)."""

import pytest

pytestmark = pytest.mark.integration


class _BrokenSession:
    """Имитация недоступной БД."""

    def execute(self, *args, **kwargs):
        raise RuntimeError("database is down")

    def close(self):
        pass


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "connected"}


def test_health_reports_503_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr("app.main.SessionLocal", _BrokenSession)
    resp = client.get("/health")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "error"
    assert body["database"] == "disconnected"
    assert "database is down" in body["error"]


def test_invalid_json_returns_422(client, admin_headers):
    resp = client.post(
        "/sales/",
        content="{not json",
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_unknown_route_returns_json_404(client):
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_openapi_docs_are_available(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "Music Store API"


def test_index_page_is_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
