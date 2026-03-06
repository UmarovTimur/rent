from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    basket: Mapped["Basket"] = relationship("Basket", back_populates="orders")  # noqa: F821

    def __str__(self) -> str:
        return f"Order #{self.order_id}"

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

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")  # noqa: F821

    def __str__(self) -> str:
        return f"OrderItem #{self.order_item_id} (product_id={self.product_id}) x{self.quantity}"

    __repr__ = __str__
