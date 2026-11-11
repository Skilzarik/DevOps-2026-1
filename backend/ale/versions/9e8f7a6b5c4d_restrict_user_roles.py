"""restrict user roles: допустимы только admin и seller

Revision ID: 9e8f7a6b5c4d
Revises: 7c1d2e3f4a5b
Create Date: 2026-10-17 15:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "9e8f7a6b5c4d"
down_revision: str | Sequence[str] | None = "7c1d2e3f4a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Неизвестные роли получают минимальные права, иначе ограничение не создастся.
    op.execute("UPDATE users SET role = 'seller' WHERE role NOT IN ('admin', 'seller')")
    op.create_check_constraint("ck_users_role_valid", "users", "role IN ('admin', 'seller')")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_users_role_valid", "users", type_="check")
