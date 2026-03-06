"""add rental dates to basket and order items

Revision ID: 9b2c1d8e7f4a
Revises: 6f4e2c1a9b7d
Create Date: 2026-02-24 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b2c1d8e7f4a'
down_revision: Union[str, None] = '6f4e2c1a9b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('basket_items', sa.Column('rental_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('basket_items', sa.Column('rental_end', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        'ck_basket_items_rental_pair',
        'basket_items',
        '(rental_start IS NULL AND rental_end IS NULL) OR '
        '(rental_start IS NOT NULL AND rental_end IS NOT NULL)',
    )
    op.create_check_constraint(
        'ck_basket_items_rental_range',
        'basket_items',
        'rental_start IS NULL OR rental_end IS NULL OR rental_end > rental_start',
    )
    op.create_index(
        'ix_basket_items_price_id_rental_start_rental_end',
        'basket_items',
        ['price_id', 'rental_start', 'rental_end'],
        unique=False,
    )

    op.add_column('order_items', sa.Column('rental_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('order_items', sa.Column('rental_end', sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        'ck_order_items_rental_pair',
        'order_items',
        '(rental_start IS NULL AND rental_end IS NULL) OR '
        '(rental_start IS NOT NULL AND rental_end IS NOT NULL)',
    )
    op.create_check_constraint(
        'ck_order_items_rental_range',
        'order_items',
        'rental_start IS NULL OR rental_end IS NULL OR rental_end > rental_start',
    )
    op.create_index(
        'ix_order_items_price_id_rental_start_rental_end',
        'order_items',
        ['price_id', 'rental_start', 'rental_end'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_order_items_price_id_rental_start_rental_end', table_name='order_items')
    op.drop_constraint('ck_order_items_rental_range', 'order_items', type_='check')
    op.drop_constraint('ck_order_items_rental_pair', 'order_items', type_='check')
    op.drop_column('order_items', 'rental_end')
    op.drop_column('order_items', 'rental_start')

    op.drop_index('ix_basket_items_price_id_rental_start_rental_end', table_name='basket_items')
    op.drop_constraint('ck_basket_items_rental_range', 'basket_items', type_='check')
    op.drop_constraint('ck_basket_items_rental_pair', 'basket_items', type_='check')
    op.drop_column('basket_items', 'rental_end')
    op.drop_column('basket_items', 'rental_start')
