"""move price to product and drop price/size tables

Revision ID: 3d1b7f4c2a11
Revises: 2c4d8f1e6a90
Create Date: 2026-02-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d1b7f4c2a11'
down_revision: Union[str, None] = '2c4d8f1e6a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index.get("name") for index in inspector.get_indexes(table_name)}
    if index_name in existing_indexes:
        op.drop_index(index_name, table_name=table_name)


def _drop_fk_by_column_if_exists(
    table_name: str,
    constrained_column: str,
    referred_table: str,
) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys(table_name):
        if (
            fk.get("referred_table") == referred_table
            and fk.get("constrained_columns") == [constrained_column]
            and fk.get("name")
        ):
            op.drop_constraint(fk["name"], table_name, type_="foreignkey")


def upgrade() -> None:
    op.add_column('products', sa.Column('price', sa.Float(), nullable=True, server_default='0'))

    op.execute(
        """
        UPDATE products
        SET price = COALESCE(
            (
                SELECT MIN(prices.price)
                FROM prices
                WHERE prices.product_id = products.product_id
            ),
            0
        )
        """
    )

    op.add_column('basket_items', sa.Column('product_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE basket_items
        SET product_id = (
            SELECT prices.product_id
            FROM prices
            WHERE prices.price_id = basket_items.price_id
        )
        """
    )

    _drop_index_if_exists('basket_items', 'ix_basket_items_price_id_rental_start_rental_end')
    _drop_fk_by_column_if_exists('basket_items', 'price_id', 'prices')
    op.create_foreign_key(
        'basket_items_product_id_fkey',
        'basket_items',
        'products',
        ['product_id'],
        ['product_id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_basket_items_product_id_rental_start_rental_end',
        'basket_items',
        ['product_id', 'rental_start', 'rental_end'],
        unique=False,
    )
    op.alter_column('basket_items', 'product_id', nullable=False)
    op.drop_column('basket_items', 'price_id')

    op.add_column('order_items', sa.Column('product_id', sa.Integer(), nullable=True))
    op.add_column('order_items', sa.Column('unit_price', sa.Float(), nullable=True))
    op.execute(
        """
        UPDATE order_items
        SET
            product_id = (
                SELECT prices.product_id
                FROM prices
                WHERE prices.price_id = order_items.price_id
            ),
            unit_price = (
                SELECT prices.price
                FROM prices
                WHERE prices.price_id = order_items.price_id
            )
        """
    )

    _drop_index_if_exists('order_items', 'ix_order_items_price_id_rental_start_rental_end')
    _drop_fk_by_column_if_exists('order_items', 'price_id', 'prices')
    op.create_foreign_key(
        'order_items_product_id_fkey',
        'order_items',
        'products',
        ['product_id'],
        ['product_id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_order_items_product_id_rental_start_rental_end',
        'order_items',
        ['product_id', 'rental_start', 'rental_end'],
        unique=False,
    )
    op.alter_column('order_items', 'product_id', nullable=False)
    op.alter_column('order_items', 'unit_price', nullable=False)
    op.drop_column('order_items', 'price_id')

    op.drop_table('prices')
    op.drop_table('sizes')

    op.alter_column('products', 'price', server_default=None, nullable=False)


def downgrade() -> None:
    op.create_table(
        'sizes',
        sa.Column('size_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint('size_id'),
        sa.UniqueConstraint('name'),
    )
    op.execute("INSERT INTO sizes (name) VALUES ('default')")

    op.create_table(
        'prices',
        sa.Column('price_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('size_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['size_id'], ['sizes.size_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('price_id'),
    )
    op.execute(
        """
        INSERT INTO prices (size_id, product_id, price)
        SELECT s.size_id, p.product_id, p.price
        FROM products p
        CROSS JOIN (
            SELECT size_id
            FROM sizes
            ORDER BY size_id
            LIMIT 1
        ) s
        """
    )

    op.add_column('basket_items', sa.Column('price_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE basket_items
        SET price_id = (
            SELECT prices.price_id
            FROM prices
            WHERE prices.product_id = basket_items.product_id
        )
        """
    )
    op.drop_index(
        'ix_basket_items_product_id_rental_start_rental_end',
        table_name='basket_items',
    )
    op.drop_constraint('basket_items_product_id_fkey', 'basket_items', type_='foreignkey')
    op.create_foreign_key(
        'basket_items_price_id_fkey',
        'basket_items',
        'prices',
        ['price_id'],
        ['price_id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_basket_items_price_id_rental_start_rental_end',
        'basket_items',
        ['price_id', 'rental_start', 'rental_end'],
        unique=False,
    )
    op.alter_column('basket_items', 'price_id', nullable=False)
    op.drop_column('basket_items', 'product_id')

    op.add_column('order_items', sa.Column('price_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE order_items
        SET price_id = (
            SELECT prices.price_id
            FROM prices
            WHERE prices.product_id = order_items.product_id
        )
        """
    )
    op.drop_index(
        'ix_order_items_product_id_rental_start_rental_end',
        table_name='order_items',
    )
    op.drop_constraint('order_items_product_id_fkey', 'order_items', type_='foreignkey')
    op.create_foreign_key(
        'order_items_price_id_fkey',
        'order_items',
        'prices',
        ['price_id'],
        ['price_id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_order_items_price_id_rental_start_rental_end',
        'order_items',
        ['price_id', 'rental_start', 'rental_end'],
        unique=False,
    )
    op.alter_column('order_items', 'price_id', nullable=False)
    op.drop_column('order_items', 'unit_price')
    op.drop_column('order_items', 'product_id')

    op.drop_column('products', 'price')
