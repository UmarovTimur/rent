from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.clients.database.base import Base

# Many-to-many: a parent product ↔ its optional add-ons (both are Product rows).
# An add-on (e.g. a night light) can be attached to several parents.
product_addon_links = Table(
    "product_addon_links",
    Base.metadata,
    Column(
        "parent_product_id",
        ForeignKey("products.product_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "addon_product_id",
        ForeignKey("products.product_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("sort_order", Integer, nullable=False, default=0),
    # How many of this child are pre-included when the parent opens.
    # 0 = optional add-on (opt-in); >0 = kit component included by default.
    Column("default_quantity", Integer, nullable=False, default=0, server_default="0"),
    extend_existing=True,
)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    product_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str] = mapped_column(nullable=True)
    image_urls: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True, default=list)
    # Add-ons are hidden from the main catalog and only offered as options on a parent.
    is_addon: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 'per_day' (× rental days, like a product) or 'flat' (charged once).
    price_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="per_day")

    # Non-mapped, admin-only: the SQLAdmin form has a virtual "upload_images" field
    # (see ProductAdmin). SQLAdmin's file handling does getattr(obj, "upload_images")
    # on edit; without this it would raise AttributeError. Not a DB column.
    upload_images = None

    @property
    def existing_photos(self) -> list[str]:
        """All current image filenames (cover first). Feeds the admin edit form's
        "delete photo" checkboxes. Not a DB column."""
        return ([self.image_url] if self.image_url else []) + list(self.image_urls or [])

    @existing_photos.setter
    def existing_photos(self, _value) -> None:
        # Admin form field is display/checkbox only — writes are handled in
        # ProductAdmin.after_model_change, so ignore direct assignment here.
        pass

    category: Mapped["Category"] = relationship(back_populates="products")  # noqa: F821

    # This product's add-ons / kit components (read-only convenience view).
    # Links (incl. default_quantity) are managed via ProductAddonLink / its admin.
    addons: Mapped[list["Product"]] = relationship(
        "Product",
        secondary=product_addon_links,
        primaryjoin=product_id == product_addon_links.c.parent_product_id,
        secondaryjoin=product_id == product_addon_links.c.addon_product_id,
        order_by=product_addon_links.c.sort_order,
        viewonly=True,
    )
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


class ProductAddonLink(Base):
    """Association object for a parent product ↔ its add-on / kit-component child.

    Carries `default_quantity` (how many of the child are pre-included on open) and
    `sort_order`. Managed directly in the admin (ProductAddonLinkAdmin).
    """

    __table__ = product_addon_links

    parent: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[product_addon_links.c.parent_product_id],
        overlaps="addons",
    )
    addon: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[product_addon_links.c.addon_product_id],
        overlaps="addons",
    )

    def __str__(self) -> str:
        return f"{self.parent} → {self.addon} ×{self.default_quantity}"

    __repr__ = __str__


from src.clients.database.models.rental import ProductRental, ProductRentalSlot  # noqa: E402,F401
