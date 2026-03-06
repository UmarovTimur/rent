from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.clients.database.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    product_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str] = mapped_column(nullable=True)

    category: Mapped["Category"] = relationship(back_populates="products")  # noqa: F821
    basket_items: Mapped[list["BasketItem"]] = relationship(
        "BasketItem",
        back_populates="product",
        cascade="all, delete-orphan",
    )  # noqa: F821
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
        cascade="all, delete-orphan",
    )  # noqa: F821
    rental_config: Mapped["ProductRental"] = relationship(  # noqa: F821
        "ProductRental",
        back_populates="product",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __str__(self) -> str:
        return self.name

    __repr__ = __str__


from src.clients.database.models.rental import ProductRental, ProductRentalSlot  # noqa: E402,F401
