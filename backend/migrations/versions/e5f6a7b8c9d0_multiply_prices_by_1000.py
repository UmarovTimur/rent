"""multiply prices by 1000

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-01

"""
from typing import Union

from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE products SET price = price * 1000")
    op.execute("UPDATE orders SET total_price = total_price * 1000")
    op.execute("UPDATE order_items SET unit_price = unit_price * 1000")


def downgrade() -> None:
    op.execute("UPDATE products SET price = price / 1000")
    op.execute("UPDATE orders SET total_price = total_price / 1000")
    op.execute("UPDATE order_items SET unit_price = unit_price / 1000")
