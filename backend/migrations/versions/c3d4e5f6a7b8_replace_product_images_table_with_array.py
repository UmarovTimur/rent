"""replace product_images table with image_urls array column

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-06-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_product_images_product_id', table_name='product_images')
    op.drop_table('product_images')
    op.add_column('products', sa.Column('image_urls', ARRAY(sa.String()), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'image_urls')
    op.create_table(
        'product_images',
        sa.Column('image_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('image_id'),
    )
    op.create_index('ix_product_images_product_id', 'product_images', ['product_id'])
