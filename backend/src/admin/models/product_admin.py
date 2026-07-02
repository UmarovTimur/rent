import asyncio
from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqlalchemy import update as sa_update
from starlette.requests import Request
from wtforms import MultipleFileField
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
        Product.image_url,
    ]
    column_details_list = [
        Product.product_id,
        Product.category,
        Product.name,
        Product.description,
        Product.price,
        Product.image_url,
        Product.image_urls,
    ]
    column_searchable_list = [Product.name]
    form_columns = [
        Product.name,
        Product.description,
        Product.category,
        Product.price,
    ]
    form_ajax_refs = {
        "category": {"fields": ["name"], "order_by": "name"},
    }
    form_widget_args = {
        "price": {"step": 1, "min": 0},
    }
    form_extra_fields = {
        "upload_images": MultipleFileField(
            "Фотографии (можно несколько)",
            validators=[Optional()],
        ),
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

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        files = data.get("upload_images") or []
        if not isinstance(files, list):
            files = [files] if files else []

        saved: list[str] = [n for n in [await _save_file(f) for f in files] if n]
        if not saved:
            return

        existing: list[str] = list(model.image_urls or [])

        # First uploaded file becomes cover image if there isn't one yet
        new_cover = model.image_url
        if not new_cover:
            new_cover = saved[0]
            remaining = saved[1:]
        else:
            remaining = saved

        new_image_urls = existing + remaining

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

    async def on_model_delete(self, model: Any, request: Request) -> None:
        for filename in [model.image_url] + list(model.image_urls or []):
            if filename:
                await delete_image(filename, products_path)
