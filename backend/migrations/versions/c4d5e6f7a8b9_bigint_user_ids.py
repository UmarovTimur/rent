"""widen user_id columns to bigint (telegram ids now exceed int32 range)

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'user_id', type_=sa.BigInteger(), existing_type=sa.Integer())
    op.alter_column('baskets', 'user_id', type_=sa.BigInteger(), existing_type=sa.Integer())
    op.alter_column('orders', 'user_id', type_=sa.BigInteger(), existing_type=sa.Integer())


def downgrade() -> None:
    op.alter_column('orders', 'user_id', type_=sa.Integer(), existing_type=sa.BigInteger())
    op.alter_column('baskets', 'user_id', type_=sa.Integer(), existing_type=sa.BigInteger())
    op.alter_column('users', 'user_id', type_=sa.Integer(), existing_type=sa.BigInteger())
