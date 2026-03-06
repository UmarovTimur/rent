"""make product prices integer and enforce legacy table cleanup

Revision ID: 8f6c2b1d4a9e
Revises: 3d1b7f4c2a11
Create Date: 2026-02-26 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f6c2b1d4a9e"
down_revision: Union[str, None] = "3d1b7f4c2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _to_int(column_name: str) -> str:
    return f"TRUNC(COALESCE({column_name}, 0))::integer"


def upgrade() -> None:
    # Safety cleanup if legacy tables still exist in the target database.
    op.execute("DROP TABLE IF EXISTS prices CASCADE")
    op.execute("DROP TABLE IF EXISTS sizes CASCADE")

    op.alter_column(
        "products",
        "price",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using=_to_int("price"),
        nullable=False,
    )
    op.alter_column(
        "order_items",
        "unit_price",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using=_to_int("unit_price"),
        nullable=False,
    )
    op.alter_column(
        "orders",
        "total_price",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using=_to_int("total_price"),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "orders",
        "total_price",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="total_price::double precision",
        nullable=False,
    )
    op.alter_column(
        "order_items",
        "unit_price",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="unit_price::double precision",
        nullable=False,
    )
    op.alter_column(
        "products",
        "price",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="price::double precision",
        nullable=False,
    )
