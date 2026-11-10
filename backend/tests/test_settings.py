"""Конфигурация приложения только через переменные окружения (ТЗ 4.3a)."""

import pytest
from pydantic import ValidationError

from app.database import Settings

pytestmark = pytest.mark.unit


def test_settings_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x_test")
    monkeypatch.setenv("SECRET_KEY", "k")
    settings = Settings(_env_file=None)
    assert settings.DATABASE_URL.endswith("/x_test")
    assert settings.SECRET_KEY == "k"


def test_database_url_is_mandatory(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SECRET_KEY", "k")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secret_key_has_no_insecure_default(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x_test")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_optional_settings_have_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/x_test")
    monkeypatch.setenv("SECRET_KEY", "k")
    monkeypatch.delenv("ALGORITHM", raising=False)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
