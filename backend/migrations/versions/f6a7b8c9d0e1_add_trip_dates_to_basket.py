"""add trip dates to basket

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('baskets', sa.Column('rental_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('baskets', sa.Column('rental_end', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        'ck_baskets_rental_pair',
        'baskets',
        '(rental_start IS NULL AND rental_end IS NULL) OR '
        '(rental_start IS NOT NULL AND rental_end IS NOT NULL)',
    )
    op.create_check_constraint(
        'ck_baskets_rental_range',
        'baskets',
        'rental_start IS NULL OR rental_end IS NULL OR rental_end > rental_start',
    )


def downgrade() -> None:
    op.drop_constraint('ck_baskets_rental_range', 'baskets', type_='check')
    op.drop_constraint('ck_baskets_rental_pair', 'baskets', type_='check')
    op.drop_column('baskets', 'rental_end')
    op.drop_column('baskets', 'rental_start')
