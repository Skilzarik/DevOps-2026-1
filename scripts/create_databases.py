"""Создаёт рабочую и тестовую базы данных, если их ещё нет (вызывается из make setup)."""

import re
import sys

from _env import lookup
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def ensure_database(url_str: str) -> None:
    url = make_url(url_str)
    name = url.database or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        sys.exit(f"Недопустимое имя базы: {name!r} (разрешены буквы, цифры и _)")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
        if exists:
            print(f"  база {name}: уже есть")
        else:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
            print(f"  база {name}: создана")
    admin.dispose()


def main() -> None:
    for var in ("DATABASE_URL", "TEST_DATABASE_URL"):
        value = lookup(var)
        if not value:
            sys.exit(f"{var} не задан: проверьте backend/.env и backend/.env.test")
        ensure_database(value)


if __name__ == "__main__":
    main()
