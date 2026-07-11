import asyncio
from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import BooleanField, Field, IntegerField, MultipleFileField, TextAreaField
from wtforms.validators import NumberRange, Optional

from src.clients.database.models.product import Product
from src.clients.database.models.rental import ProductRental
from src.container import container
from src.services.schemas import Image
from src.services.static import products_path
from src.services.utils import delete_image, save_image


def _img_tag(filename: str) -> str:
    return (
        f'<img src="/media/products/{filename}" '
        f'style="height:72px;width:72px;object-fit:cover;border-radius:8px;margin:2px;" />'
    )


class _DeletableImagesWidget:
    """Renders current product photos as thumbnails, each with an order number
    input (reorder) and a "delete" checkbox. The order/filename pairs are read
    back from the raw form in ProductAdmin.after_model_change."""

    def __call__(self, field: "ExistingPhotosField", **kwargs: Any) -> Markup:
        images = list(field.object_data or [])
        if not images:
            return Markup('<div style="opacity:.6">Нет загруженных фото</div>')
        checked = set(field.data or [])
        parts = [
            '<div style="opacity:.7;font-size:12px;margin-bottom:6px;">'
            "№ — порядок (1 = обложка), меняйте числа чтобы переставить</div>",
            '<div style="display:flex;flex-wrap:wrap;gap:12px;">',
        ]
        for i, fn in enumerate(images):
            hidden = f'<input type="hidden" name="photo_file" value="{fn}">'
            order = (
                f'<input type="number" name="photo_order" value="{i + 1}" min="1" '
                'style="width:60px;text-align:center;">'
            )
            box = (
                f'<input type="checkbox" name="{field.name}" value="{fn}" '
                f'{"checked" if fn in checked else ""}>'
            )
            img = (
                f'<img src="/media/products/{fn}" '
                f'style="height:84px;width:84px;object-fit:cover;border-radius:8px;display:block;" />'
            )
            parts.append(
                '<div style="display:inline-flex;flex-direction:column;align-items:center;gap:4px;">'
                f'{img}{hidden}'
                f'<span style="font-size:12px;">№ {order}</span>'
                f'<label style="font-size:12px;cursor:pointer;">{box} удалить</label></div>'
            )
        parts.append("</div>")
        return Markup("".join(parts))


class ExistingPhotosField(Field):
    """Read-existing / mark-for-delete field. Submitted data = filenames to remove."""

    widget = _DeletableImagesWidget()

    def process_data(self, value: Any) -> None:
        # `value` = model.existing_photos (current filenames); nothing selected yet.
        self.data = []

    def process_formdata(self, valuelist: list[str]) -> None:
        # Checked boxes = filenames the admin wants to delete.
        self.data = list(valuelist)


async def _save_file(file: Any) -> str | None:
    filename = getattr(file, "filename", None)
    if not filename:
        return None
    read_fn = getattr(file, "read", None)
    if not read_fn:
        return None
    contents = await read_fn() if asyncio.iscoroutinefunction(read_fn) else read_fn()
    if not contents:
        return None
    return await save_image(Image(file_bytes=contents, filename=filename), products_path)


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
        Product.image_url: lambda m, a: Markup(_img_tag(m.image_url)) if m.image_url else "—",
    }
    column_formatters_detail = {
        Product.image_url: lambda m, a: Markup(_img_tag(m.image_url)) if m.image_url else "—",
        Product.image_urls: lambda m, a: (
            Markup("".join(_img_tag(u) for u in m.image_urls))
            if m.image_urls else "—"
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
        # sqladmin 0.20 dropped `form_extra_fields`; inject the photo fields by
        # subclassing the generated form (metaclass picks them up).
        form_class = await super().scaffold_form(rules)

        class ProductForm(form_class):  # type: ignore[valid-type, misc]
            # Current photos with a "delete" checkbox each (populated from
            # Product.existing_photos on edit).
            existing_photos = ExistingPhotosField("Текущие фото (отметьте, чтобы удалить)")
            upload_images = MultipleFileField(
                "Добавить фото (можно несколько)",
                validators=[Optional()],
            )
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

        # Photos checked for deletion.
        to_delete = set(data.get("existing_photos") or [])

        # Newly uploaded files.
        files = data.get("upload_images") or []
        if not isinstance(files, list):
            files = [files] if files else []
        saved: list[str] = [n for n in [await _save_file(f) for f in files] if n]

        # Reorder: read the per-photo (filename, position) pairs from the raw form
        # (rendered by _DeletableImagesWidget). Starlette caches request.form().
        ordered_current: list[str] = []
        try:
            form = await request.form()
            filenames = form.getlist("photo_file")
            orders = form.getlist("photo_order")
        except Exception:
            filenames, orders = [], []

        if filenames and len(filenames) == len(orders):
            def _pos(pair: tuple[str, str]) -> int:
                try:
                    return int(pair[1])
                except (TypeError, ValueError):
                    return 10**9
            ordered_current = [fn for fn, _ in sorted(zip(filenames, orders), key=_pos)]
        else:
            ordered_current = ([model.image_url] if model.image_url else []) + list(
                model.image_urls or []
            )

        if not to_delete and not saved and not filenames:
            return

        # Apply deletions, keep the chosen order, append new uploads at the end.
        kept = [fn for fn in ordered_current if fn not in to_delete] + saved

        new_cover = kept[0] if kept else None
        new_image_urls = kept[1:]

        db = container.database()
        async with db.session() as session:
            await session.execute(
                sa_update(Product)
                .where(Product.product_id == model.product_id)
                .values(image_url=new_cover, image_urls=new_image_urls)
            )
            await session.commit()
        model.image_url = new_cover
        model.image_urls = new_image_urls

        # Remove deleted files from disk (only after the DB no longer references them).
        for filename in to_delete:
            await delete_image(filename, products_path)

    async def on_model_delete(self, model: Any, request: Request) -> None:
        for filename in [model.image_url] + list(model.image_urls or []):
            if filename:
                await delete_image(filename, products_path)
