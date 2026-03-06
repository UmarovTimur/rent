from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.clients.database.base import Base


class Basket(Base):
    __tablename__ = "baskets"

    basket_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    discount: Mapped[float] = mapped_column(nullable=True)

    items: Mapped[list["BasketItem"]] = relationship(
        "BasketItem", back_populates="basket", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="basket", cascade="all, delete-orphan")  # noqa: F821

    def __str__(self) -> str:
        return f"Basket #{self.basket_id}"

    __repr__ = __str__


class BasketItem(Base):
    __tablename__ = "basket_items"
    __table_args__ = (
        CheckConstraint(
            "(rental_start IS NULL AND rental_end IS NULL) OR "
            "(rental_start IS NOT NULL AND rental_end IS NOT NULL)",
            name="ck_basket_items_rental_pair",
        ),
        CheckConstraint(
            "rental_start IS NULL OR rental_end IS NULL OR rental_end > rental_start",
            name="ck_basket_items_rental_range",
        ),
    )

    basket_item_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    basket_id: Mapped[int] = mapped_column(ForeignKey("baskets.basket_id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    rental_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    rental_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    basket: Mapped["Basket"] = relationship("Basket", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="basket_items")  # noqa: F821

    def __str__(self) -> str:
        return f"BasketItem #{self.basket_item_id} (product_id={self.product_id}) x{self.quantity}"

    __repr__ = __str__
