"""add reminder flags to orders

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('pickup_reminder_sent', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('orders', sa.Column('return_reminder_sent', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('orders', 'return_reminder_sent')
    op.drop_column('orders', 'pickup_reminder_sent')
