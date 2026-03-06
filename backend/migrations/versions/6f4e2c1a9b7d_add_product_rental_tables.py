"""add product rental tables

Revision ID: 6f4e2c1a9b7d
Revises: cb510355b1bd
Create Date: 2026-02-24 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f4e2c1a9b7d'
down_revision: Union[str, None] = 'cb510355b1bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_rentals',
        sa.Column('rental_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('total_quantity', sa.Integer(), nullable=False),
        sa.Column('slot_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('min_rental_slots', sa.Integer(), nullable=False),
        sa.Column('max_rental_slots', sa.Integer(), nullable=True),
        sa.Column('buffer_before_minutes', sa.Integer(), nullable=False),
        sa.Column('buffer_after_minutes', sa.Integer(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('buffer_after_minutes >= 0', name='ck_product_rentals_buffer_after_non_negative'),
        sa.CheckConstraint('buffer_before_minutes >= 0', name='ck_product_rentals_buffer_before_non_negative'),
        sa.CheckConstraint(
            'max_rental_slots IS NULL OR max_rental_slots >= min_rental_slots',
            name='ck_product_rentals_max_slots_valid',
        ),
        sa.CheckConstraint('min_rental_slots > 0', name='ck_product_rentals_min_slots_positive'),
        sa.CheckConstraint('slot_duration_minutes > 0', name='ck_product_rentals_slot_duration_positive'),
        sa.CheckConstraint('total_quantity >= 0', name='ck_product_rentals_total_quantity_non_negative'),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('rental_id'),
        sa.UniqueConstraint('product_id', name='uq_product_rentals_product_id'),
    )
    op.create_table(
        'product_rental_slots',
        sa.Column('slot_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rental_id', sa.Integer(), nullable=False),
        sa.Column('slot_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('slot_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reserved_quantity', sa.Integer(), nullable=False),
        sa.Column('blocked_quantity', sa.Integer(), nullable=False),
        sa.Column('capacity_override', sa.Integer(), nullable=True),
        sa.Column('is_closed', sa.Boolean(), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            'capacity_override IS NULL OR capacity_override >= 0',
            name='ck_product_rental_slots_capacity_non_negative',
        ),
        sa.CheckConstraint('blocked_quantity >= 0', name='ck_product_rental_slots_blocked_non_negative'),
        sa.CheckConstraint('reserved_quantity >= 0', name='ck_product_rental_slots_reserved_non_negative'),
        sa.CheckConstraint('slot_end > slot_start', name='ck_product_rental_slots_valid_range'),
        sa.ForeignKeyConstraint(['rental_id'], ['product_rentals.rental_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('slot_id'),
        sa.UniqueConstraint('rental_id', 'slot_start', 'slot_end', name='uq_product_rental_slots_slot_range'),
    )
    op.create_index(
        'ix_product_rental_slots_rental_id_slot_start',
        'product_rental_slots',
        ['rental_id', 'slot_start'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_product_rental_slots_rental_id_slot_start', table_name='product_rental_slots')
    op.drop_table('product_rental_slots')
    op.drop_table('product_rentals')
