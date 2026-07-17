"""add order google_event_id

Revision ID: a3f8c2e1d9b0
Revises: 9e8d7c6b5a4f
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c2e1d9b0'
down_revision: Union[str, None] = '9e8d7c6b5a4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('google_event_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'google_event_id')
