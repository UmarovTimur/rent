from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.clients.database.base import Base


class ProductRental(Base):
    __tablename__ = "product_rentals"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_product_rentals_product_id"),
        CheckConstraint("total_quantity >= 0", name="ck_product_rentals_total_quantity_non_negative"),
        CheckConstraint("slot_duration_minutes > 0", name="ck_product_rentals_slot_duration_positive"),
        CheckConstraint("min_rental_slots > 0", name="ck_product_rentals_min_slots_positive"),
        CheckConstraint("buffer_before_minutes >= 0", name="ck_product_rentals_buffer_before_non_negative"),
        CheckConstraint("buffer_after_minutes >= 0", name="ck_product_rentals_buffer_after_non_negative"),
        CheckConstraint(
            "max_rental_slots IS NULL OR max_rental_slots >= min_rental_slots",
            name="ck_product_rentals_max_slots_valid",
        ),
    )

    rental_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    total_quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    slot_duration_minutes: Mapped[int] = mapped_column(nullable=False, default=60)
    min_rental_slots: Mapped[int] = mapped_column(nullable=False, default=1)
    max_rental_slots: Mapped[int] = mapped_column(nullable=True)
    buffer_before_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    buffer_after_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    product: Mapped["Product"] = relationship("Product", back_populates="rental_config")  # noqa: F821
    slots: Mapped[list["ProductRentalSlot"]] = relationship(  # noqa: F821
        "ProductRentalSlot",
        back_populates="rental",
        cascade="all, delete-orphan",
    )

    def __str__(self) -> str:
        return f"Rental #{self.rental_id} (product_id={self.product_id})"

    __repr__ = __str__


class ProductRentalSlot(Base):
    __tablename__ = "product_rental_slots"
    __table_args__ = (
        UniqueConstraint("rental_id", "slot_start", "slot_end", name="uq_product_rental_slots_slot_range"),
        CheckConstraint("slot_end > slot_start", name="ck_product_rental_slots_valid_range"),
        CheckConstraint("reserved_quantity >= 0", name="ck_product_rental_slots_reserved_non_negative"),
        CheckConstraint("blocked_quantity >= 0", name="ck_product_rental_slots_blocked_non_negative"),
        CheckConstraint(
            "capacity_override IS NULL OR capacity_override >= 0",
            name="ck_product_rental_slots_capacity_non_negative",
        ),
    )

    slot_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rental_id: Mapped[int] = mapped_column(ForeignKey("product_rentals.rental_id", ondelete="CASCADE"), nullable=False)
    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    blocked_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    capacity_override: Mapped[int] = mapped_column(nullable=True)
    is_closed: Mapped[bool] = mapped_column(nullable=False, default=False)
    note: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    rental: Mapped["ProductRental"] = relationship("ProductRental", back_populates="slots")

    def __str__(self) -> str:
        return f"Slot #{self.slot_id}: {self.slot_start} - {self.slot_end}"

    __repr__ = __str__
