"""Аутентификация и авторизация через API (ТЗ 4.3b, 6.4)."""

import pytest
from sqlalchemy import text

from app import auth
from helpers import PASSWORD, auth_header

pytestmark = pytest.mark.integration


def _register(client, username="alice", role="seller", password=PASSWORD):
    return client.post(
        "/auth/register", json={"username": username, "password": password, "role": role}
    )


def test_register_creates_user_without_exposing_password(client):
    resp = _register(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "seller"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_username_rejected(client):
    assert _register(client).status_code == 200
    resp = _register(client)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_register_unknown_role_rejected(client):
    assert _register(client, role="superuser").status_code == 422


def test_register_requires_password(client):
    resp = client.post("/auth/register", json={"username": "alice"})
    assert resp.status_code == 422


def test_password_is_stored_hashed(client, db):
    _register(client)
    stored = db.execute(
        text("SELECT hashed_password FROM users WHERE username = 'alice'")
    ).scalar_one()
    assert stored != PASSWORD
    assert stored.startswith("$2")


def test_login_returns_bearer_token(client):
    _register(client)
    resp = client.post("/auth/login", json={"username": "alice", "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    me = client.get("/auth/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_login_wrong_password_rejected(client):
    _register(client)
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post("/auth/login", json={"username": "nobody", "password": PASSWORD})
    assert resp.status_code == 401


def test_me_requires_token(client):
    # Код ответа без токена зависит от версии FastAPI (401 или 403): оба означают отказ.
    assert client.get("/auth/me").status_code in (401, 403)


def test_me_rejects_invalid_token(client):
    resp = client.get("/auth/me", headers=auth_header("not.a.jwt"))
    assert resp.status_code == 401


def test_token_for_unknown_user_rejected(client):
    token = auth.create_access_token({"sub": "ghost"})
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_token_without_subject_rejected(client):
    token = auth.create_access_token({})
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401
