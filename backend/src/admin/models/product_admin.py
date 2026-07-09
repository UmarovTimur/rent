import asyncio
from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqlalchemy import update as sa_update
from starlette.requests import Request
from wtforms import Field, MultipleFileField, TextAreaField
from wtforms.validators import Optional

from src.clients.database.models.product import Product
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
    ]
    # Parent → child links (incl. per-kit default quantity) are managed in the
    # dedicated "Kit / add-on links" section (ProductAddonLinkAdmin).
    form_ajax_refs = {
        "category": {"fields": ["name"], "order_by": "name"},
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

        return ProductForm

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
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
