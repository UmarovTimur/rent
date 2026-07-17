"""add promos table

Revision ID: c1d2e3f4a5b6
Revises: 9f8e7d6c5b4a
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = '9f8e7d6c5b4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'promos',
        sa.Column('promo_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=60), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('image_urls', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('promo_id'),
    )


def downgrade() -> None:
    op.drop_table('promos')
