"""Миграции Alembic: чистая БД, БД с данными, откат, соответствие моделям (Лаб. 3, п. 8-9)."""

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models import Base
from helpers import alembic_config, reset_schema

pytestmark = [pytest.mark.integration, pytest.mark.migrations]

INIT_REVISION = "53ee2a3cf30d"
APP_TABLES = {"users", "musicians", "discs", "sales"}


@pytest.fixture
def blank_db(engine):
    """Пустая схема. После теста общая тестовая схема возвращается к актуальной версии."""
    reset_schema(engine)
    yield engine
    from app.database import engine as app_engine

    reset_schema(engine)
    command.upgrade(alembic_config(), "head")
    app_engine.dispose()


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _seed_valid_rows(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, hashed_password, role) "
                "VALUES (1, 'u', 'h', 'admin')"
            )
        )
        conn.execute(text("INSERT INTO musicians (id, name, genre) VALUES (1, 'm', 'g')"))
        conn.execute(
            text(
                "INSERT INTO discs (id, title, musician_id, price, stock) VALUES (1, 'd', 1, 10, 5)"
            )
        )


def test_history_is_linear_and_has_at_least_three_revisions():
    script = ScriptDirectory.from_config(alembic_config())
    assert len(script.get_heads()) == 1
    assert len(list(script.walk_revisions())) >= 3


def test_clean_db_is_created_by_migrations(blank_db):
    command.upgrade(alembic_config(), "head")
    assert APP_TABLES | {"alembic_version"} <= _tables(blank_db)
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    with blank_db.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == head


def test_downgrade_to_base_and_upgrade_again(blank_db):
    cfg = alembic_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert _tables(blank_db) == {"alembic_version"}
    command.upgrade(cfg, "head")
    assert APP_TABLES <= _tables(blank_db)


def test_upgrade_keeps_existing_data_and_fixes_invalid_values(blank_db):
    cfg = alembic_config()
    command.upgrade(cfg, INIT_REVISION)
    with blank_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, hashed_password, role) "
                "VALUES (1, 'boss', 'h', 'admin'), (2, 'temp', 'h', 'manager')"
            )
        )
        conn.execute(text("INSERT INTO musicians (id, name, genre) VALUES (1, 'Muse', 'Rock')"))
        conn.execute(
            text(
                "INSERT INTO discs (id, title, musician_id, price, stock) "
                "VALUES (1, 'ok', 1, 10, 5), (2, 'broken', 1, 20, -3)"
            )
        )
        conn.execute(
            text("INSERT INTO sales (id, disc_id, quantity, total_price) VALUES (1, 1, 2, 20)")
        )

    command.upgrade(cfg, "head")

    with blank_db.connect() as conn:
        roles = dict(conn.execute(text("SELECT username, role FROM users")).all())
        stock = dict(conn.execute(text("SELECT id, stock FROM discs")).all())
        sale = conn.execute(text("SELECT disc_id, quantity, total_price FROM sales")).one()
    assert roles == {"boss": "admin", "temp": "seller"}
    assert stock == {1: 5, 2: 0}
    assert tuple(sale) == (1, 2, 20.0)


@pytest.mark.parametrize(
    ("statement", "constraint"),
    [
        (
            "INSERT INTO discs (title, musician_id, price, stock) VALUES ('x', 1, 0, 1)",
            "ck_discs_price_positive",
        ),
        (
            "INSERT INTO discs (title, musician_id, price, stock) VALUES ('x', 1, -1, 1)",
            "ck_discs_price_positive",
        ),
        (
            "INSERT INTO discs (title, musician_id, price, stock) VALUES ('x', 1, 5, -1)",
            "ck_discs_stock_non_negative",
        ),
        (
            "INSERT INTO sales (disc_id, quantity, total_price) VALUES (1, 0, 0)",
            "ck_sales_quantity_positive",
        ),
        (
            "INSERT INTO sales (disc_id, quantity, total_price) VALUES (1, 1, -5)",
            "ck_sales_total_price_non_negative",
        ),
        (
            "INSERT INTO users (username, hashed_password, role) VALUES ('x', 'h', 'hacker')",
            "ck_users_role_valid",
        ),
    ],
)
def test_database_rejects_invalid_rows(blank_db, statement, constraint):
    command.upgrade(alembic_config(), "head")
    _seed_valid_rows(blank_db)
    with pytest.raises(IntegrityError) as exc:
        with blank_db.begin() as conn:
            conn.execute(text(statement))
    assert exc.value.orig.diag.constraint_name == constraint


def test_models_match_migrations(blank_db):
    command.upgrade(alembic_config(), "head")
    with blank_db.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": False})
        assert compare_metadata(context, Base.metadata) == []
