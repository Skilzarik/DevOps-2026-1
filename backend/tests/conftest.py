"""Общие фикстуры и правила изоляции тестовых данных.

* Интеграционные тесты работают только с БД из TEST_DATABASE_URL, а имя базы обязано
  оканчиваться на ``_test``: рабочая база защищена от случайной очистки.
* Схема тестовой БД создаётся теми же миграциями, что и на проде (alembic upgrade head).
* Перед каждым интеграционным тестом таблицы очищаются (TRUNCATE ... RESTART IDENTITY).
* Unit-тесты базу не используют (``make test-unit``).
"""

import os
import secrets

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from helpers import PASSWORD, alembic_config, auth_header, reset_schema

TEST_URL = os.environ.get("TEST_DATABASE_URL")

# Для unit-тестов нужен лишь валидный URL: соединение с ним не открывается.
_UNIT_ONLY_URL = "postgresql+psycopg://unit:unit@localhost:5432/unit_only_test"

# Настройки приложения читаются при импорте app.*, поэтому подменяем их заранее.
# Секрет для токенов случайный на каждый запуск: в репозитории его нет.
os.environ["DATABASE_URL"] = TEST_URL or _UNIT_ONLY_URL
os.environ["SECRET_KEY"] = secrets.token_hex(32)
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"


def require_test_url() -> str:
    if not TEST_URL:
        pytest.fail(
            "TEST_DATABASE_URL не задан. Запускайте тесты через `make test` "
            "(см. backend/.env.test.example).",
            pytrace=False,
        )
    database = make_url(TEST_URL).database or ""
    if not database.endswith("_test"):
        pytest.fail(
            f"Опасно: база '{database}' не оканчивается на _test. Тесты остановлены.",
            pytrace=False,
        )
    return TEST_URL


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(require_test_url())
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def migrated_engine(engine):
    """Чистая тестовая БД, созданная миграциями."""
    from alembic import command

    reset_schema(engine)
    command.upgrade(alembic_config(), "head")
    return engine


@pytest.fixture
def clean_db(migrated_engine):
    with migrated_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE sales, discs, musicians, users RESTART IDENTITY CASCADE"))
    return migrated_engine


@pytest.fixture
def db(clean_db):
    """Соединение для проверок состояния БД напрямую (только чтение)."""
    with clean_db.connect() as conn:
        yield conn


@pytest.fixture
def client(clean_db):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_headers(client):
    """Фабрика: регистрирует пользователя и возвращает заголовок с его JWT."""

    def _make(username: str, role: str) -> dict[str, str]:
        reg = client.post(
            "/auth/register", json={"username": username, "password": PASSWORD, "role": role}
        )
        assert reg.status_code == 200, reg.text
        login = client.post("/auth/login", json={"username": username, "password": PASSWORD})
        assert login.status_code == 200, login.text
        return auth_header(login.json()["access_token"])

    return _make


@pytest.fixture
def admin_headers(make_headers):
    return make_headers("admin1", "admin")


@pytest.fixture
def seller_headers(make_headers):
    return make_headers("seller1", "seller")


@pytest.fixture
def musician(client, admin_headers):
    resp = client.post("/musicians/", json={"name": "Muse", "genre": "Rock"}, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def disc(client, admin_headers, musician):
    resp = client.post(
        "/discs/",
        json={"title": "Absolution", "musician_id": musician["id"], "price": 10.0, "stock": 5},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
