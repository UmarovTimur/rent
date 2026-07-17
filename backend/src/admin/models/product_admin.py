from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import BooleanField, IntegerField, TextAreaField
from wtforms.validators import NumberRange, Optional

from src.admin.photo_form import apply_photo_changes, attach_photo_fields, img_tag
from src.clients.database.models.product import Product
from src.clients.database.models.rental import ProductRental
from src.container import container
from src.services.static import products_path
from src.services.utils import delete_image

_MEDIA = "/media/products/"


class ProductAdmin(ModelView, model=Product):
    column_list = [
        Product.product_id,
        Product.category,
        Product.name,
        Product.price,
        Product.price_mode,
        Product.is_addon,
        Product.image_url,
    ]
    column_details_list = [
        Product.product_id,
        Product.category,
        Product.name,
        Product.description,
        Product.price,
        Product.price_mode,
        Product.is_addon,
        Product.addons,
        Product.image_url,
        Product.image_urls,
    ]
    column_searchable_list = [Product.name]
    form_columns = [
        Product.name,
        Product.description,
        Product.category,
        Product.price,
        Product.price_mode,
        Product.is_addon,
        Product.addon_products,
    ]
    column_labels = {
        Product.addon_products: "Аддоны / комплект (доп. продукты)",
    }
    # Attach/detach add-ons inline; per-link default quantity (kit components) is
    # still tuned in the dedicated "Kit / add-on links" section (ProductAddonLinkAdmin).
    form_ajax_refs = {
        "category": {"fields": ["name"], "order_by": "name"},
        "addon_products": {"fields": ["name"], "order_by": "name"},
    }
    # Multiline title/description so line breaks can be entered and are preserved.
    form_overrides = {
        "name": TextAreaField,
        "description": TextAreaField,
    }
    form_widget_args = {
        "price": {"step": 1, "min": 0},
        "name": {"rows": 2},
        "description": {"rows": 5},
    }
    column_formatters = {
        Product.image_url: lambda m, a: Markup(img_tag(m.image_url, _MEDIA)) if m.image_url else "—",
    }
    column_formatters_detail = {
        Product.image_url: lambda m, a: Markup(img_tag(m.image_url, _MEDIA)) if m.image_url else "—",
        Product.image_urls: lambda m, a: (
            Markup("".join(img_tag(u, _MEDIA) for u in m.image_urls)) if m.image_urls else "—"
        ),
    }
    name_plural = "Products"

    def form_edit_query(self, request: Request):
        # Eager-load the 1:1 rental config (for the virtual rental_* fields) and the
        # add-on links, so the form prefills without an async lazy-load.
        return (
            super()
            .form_edit_query(request)
            .options(selectinload(Product.rental_config), selectinload(Product.addon_products))
        )

    async def on_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        # A product can't be its own add-on — drop any self-reference from the selection.
        selected = data.get("addon_products")
        if selected and getattr(model, "product_id", None) is not None:
            data["addon_products"] = [p for p in selected if getattr(p, "product_id", None) != model.product_id]

    async def scaffold_form(self, rules=None):
        # sqladmin 0.20 dropped `form_extra_fields`; inject fields by subclassing the
        # generated form (metaclass picks them up): shared photo fields + rental config.
        form_class = attach_photo_fields(await super().scaffold_form(rules), _MEDIA)

        class ProductForm(form_class):  # type: ignore[valid-type, misc]
            # Rental config (1:1 ProductRental), edited inline — persisted in
            # after_model_change. Prefilled from Product.rental_* properties.
            rental_total_quantity = IntegerField(
                "Количество (в аренде)", validators=[Optional(), NumberRange(min=0)]
            )
            rental_slot_duration_minutes = IntegerField(
                "Длительность слота, мин", validators=[Optional(), NumberRange(min=1)]
            )
            rental_is_enabled = BooleanField("Аренда включена")

        return ProductForm

    @staticmethod
    async def _upsert_rental_config(model: Any, data: dict) -> None:
        """Persist the inline rental fields into the 1:1 ProductRental row.

        Updates the existing row, or creates one (ORM defaults cover the columns
        not exposed on the form — see rental.py). Empty numeric fields fall back to
        sensible defaults only when creating.
        """
        total_quantity = data.get("rental_total_quantity")
        slot_minutes = data.get("rental_slot_duration_minutes")
        is_enabled = bool(data.get("rental_is_enabled"))

        db = container.database()
        async with db.session() as session:
            result = await session.execute(
                select(ProductRental).where(ProductRental.product_id == model.product_id)
            )
            rental = result.scalar_one_or_none()
            if rental is not None:
                if total_quantity is not None:
                    rental.total_quantity = total_quantity
                if slot_minutes is not None:
                    rental.slot_duration_minutes = slot_minutes
                rental.is_enabled = is_enabled
            else:
                session.add(
                    ProductRental(
                        product_id=model.product_id,
                        total_quantity=total_quantity if total_quantity is not None else 1,
                        slot_duration_minutes=slot_minutes if slot_minutes is not None else 1440,
                        is_enabled=is_enabled,
                    )
                )
            await session.commit()

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        await self._upsert_rental_config(model, data)
        await apply_photo_changes(model, data, request, Product, products_path)

    async def on_model_delete(self, model: Any, request: Request) -> None:
        for filename in [model.image_url] + list(model.image_urls or []):
            if filename:
                await delete_image(filename, products_path)
