"""add product add-ons (options)

Revision ID: c7d8e9f0a1b2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'products',
        sa.Column('is_addon', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'products',
        sa.Column('price_mode', sa.String(length=16), nullable=False, server_default='per_day'),
    )

    op.create_table(
        'product_addon_links',
        sa.Column('parent_product_id', sa.Integer(), nullable=False),
        sa.Column('addon_product_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['parent_product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['addon_product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('parent_product_id', 'addon_product_id'),
    )

    op.add_column(
        'basket_items',
        sa.Column('parent_basket_item_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_basket_items_parent',
        'basket_items',
        'basket_items',
        ['parent_basket_item_id'],
        ['basket_item_id'],
        ondelete='CASCADE',
    )

    op.add_column(
        'order_items',
        sa.Column('parent_order_item_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_order_items_parent',
        'order_items',
        'order_items',
        ['parent_order_item_id'],
        ['order_item_id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_order_items_parent', 'order_items', type_='foreignkey')
    op.drop_column('order_items', 'parent_order_item_id')

    op.drop_constraint('fk_basket_items_parent', 'basket_items', type_='foreignkey')
    op.drop_column('basket_items', 'parent_basket_item_id')

    op.drop_table('product_addon_links')

    op.drop_column('products', 'price_mode')
    op.drop_column('products', 'is_addon')
