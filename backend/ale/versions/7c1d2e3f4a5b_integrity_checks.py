"""integrity checks: цена, остаток и количество не могут быть некорректными

Revision ID: 7c1d2e3f4a5b
Revises: 53ee2a3cf30d
Create Date: 2026-10-17 15:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "7c1d2e3f4a5b"
down_revision: str | Sequence[str] | None = "53ee2a3cf30d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # В уже заполненной БД могут быть некорректные значения: сначала исправляем данные,
    # иначе ограничение не создастся.
    op.execute("UPDATE discs SET stock = 0 WHERE stock < 0")
    op.create_check_constraint("ck_discs_price_positive", "discs", "price > 0")
    op.create_check_constraint("ck_discs_stock_non_negative", "discs", "stock >= 0")
    op.create_check_constraint("ck_sales_quantity_positive", "sales", "quantity > 0")
    op.create_check_constraint("ck_sales_total_price_non_negative", "sales", "total_price >= 0")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_sales_total_price_non_negative", "sales", type_="check")
    op.drop_constraint("ck_sales_quantity_positive", "sales", type_="check")
    op.drop_constraint("ck_discs_stock_non_negative", "discs", type_="check")
    op.drop_constraint("ck_discs_price_positive", "discs", type_="check")
