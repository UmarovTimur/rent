from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from src.clients.database.base import Base


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    basket_id: Mapped[int] = mapped_column(ForeignKey("baskets.basket_id", ondelete="CASCADE"), nullable=False)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_option: Mapped[str] = mapped_column(String(50), nullable=False, default="сard")
    comment: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")
    first_name: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(50), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    discount: Mapped[float] = mapped_column(nullable=True)
    pickup_reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    return_reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # Payment hold: while status == "created" and this is in the future, the order
    # blocks availability like a confirmed one. Once it passes, the order stops
    # blocking (but isn't deleted/cancelled) unless a conflict forces cancellation —
    # see RentalService._get_order_reservations and tasks/payment_holds.py.
    payment_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Google Calendar event id once this order is synced (confirmed orders only —
    # see services/calendar_sync.py). NULL if never synced or the event was deleted
    # (e.g. on cancellation).
    google_event_id: Mapped[str | None] = mapped_column(nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    basket: Mapped["Basket"] = relationship("Basket", back_populates="orders")  # noqa: F821

    def __str__(self) -> str:
        customer = self.first_name or self.phone or "—"
        return f"Order #{self.order_id} ({customer})"

    __repr__ = __str__

class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(
            "(rental_start IS NULL AND rental_end IS NULL) OR "
            "(rental_start IS NOT NULL AND rental_end IS NOT NULL)",
            name="ck_order_items_rental_pair",
        ),
        CheckConstraint(
            "rental_start IS NULL OR rental_end IS NULL OR rental_end > rental_start",
            name="ck_order_items_rental_range",
        ),
    )

    order_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    rental_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    rental_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # Snapshot of the add-on → parent-line link (NULL for normal product lines).
    parent_order_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_items.order_item_id", ondelete="CASCADE"), nullable=True
    )

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")  # noqa: F821
    addon_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        backref=backref("parent_item", remote_side=[order_item_id]),
        cascade="all, delete-orphan",
    )

    def __str__(self) -> str:
        return f"OrderItem #{self.order_item_id} (product_id={self.product_id}) x{self.quantity}"

    __repr__ = __str__
