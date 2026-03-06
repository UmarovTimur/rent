"""drop food specific entities and columns

Revision ID: 2c4d8f1e6a90
Revises: 9b2c1d8e7f4a
Create Date: 2026-02-24 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c4d8f1e6a90'
down_revision: Union[str, None] = '9b2c1d8e7f4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('order_item_excluded_ingredients')
    op.drop_table('basket_item_excluded_ingredients')
    op.drop_table('product_ingredient')
    op.drop_table('ingredients')

    op.drop_column('orders', 'time_taken')

    op.drop_column('prices', 'proteins')
    op.drop_column('prices', 'fats')
    op.drop_column('prices', 'carbohydrates')
    op.drop_column('prices', 'calories')
    op.drop_column('prices', 'is_custom')

    op.drop_column('sizes', 'grams')


def downgrade() -> None:
    op.add_column('sizes', sa.Column('grams', sa.Integer(), nullable=True))

    op.add_column('prices', sa.Column('is_custom', sa.Boolean(), nullable=True))
    op.add_column('prices', sa.Column('calories', sa.Float(), nullable=True))
    op.add_column('prices', sa.Column('carbohydrates', sa.Float(), nullable=True))
    op.add_column('prices', sa.Column('fats', sa.Float(), nullable=True))
    op.add_column('prices', sa.Column('proteins', sa.Float(), nullable=True))

    op.add_column('orders', sa.Column('time_taken', sa.String(length=50), nullable=True))

    op.create_table(
        'ingredients',
        sa.Column('ingredient_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('color', sa.Text(), nullable=True),
        sa.Column('type', sa.Text(), nullable=True),
        sa.Column('grams', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('ingredient_id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'product_ingredient',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.ingredient_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'ingredient_id'),
    )

    op.create_table(
        'basket_item_excluded_ingredients',
        sa.Column('basket_item_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['basket_item_id'], ['basket_items.basket_item_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.ingredient_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('basket_item_id', 'ingredient_id'),
    )

    op.create_table(
        'order_item_excluded_ingredients',
        sa.Column('order_item_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.order_item_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.ingredient_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('order_item_id', 'ingredient_id'),
    )
