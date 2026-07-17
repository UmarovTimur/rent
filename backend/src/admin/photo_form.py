"""Shared multi-photo admin form helpers.

Renders current images as reorderable thumbnails with per-image "delete" checkboxes
plus a multi-file upload, and persists the result (cover = image_url, rest =
image_urls). Used by ProductAdmin and PromoAdmin; parametrised by the media
sub-path so each entity serves its files from /media/<subdir>/.
"""

import asyncio
from typing import Any

from markupsafe import Markup
from sqlalchemy import update as sa_update
from starlette.requests import Request
from wtforms import Field, MultipleFileField
from wtforms.validators import Optional

from src.container import container
from src.services.schemas import Image
from src.services.utils import delete_image, save_image


def img_tag(filename: str, media_prefix: str) -> str:
    return (
        f'<img src="{media_prefix}{filename}" '
        f'style="height:72px;width:72px;object-fit:cover;border-radius:8px;margin:2px;" />'
    )


class _DeletableImagesWidget:
    """Thumbnails with an order number (reorder) and a delete checkbox each.
    Order/filename pairs are read back from the raw form in apply_photo_changes."""

    def __call__(self, field: "ExistingPhotosField", **kwargs: Any) -> Markup:
        images = list(field.object_data or [])
        prefix = field.media_prefix
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
                f'<img src="{prefix}{fn}" '
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

    def __init__(self, label: str | None = None, media_prefix: str = "/media/products/", **kwargs: Any) -> None:
        super().__init__(label, **kwargs)
        self.media_prefix = media_prefix

    def process_data(self, value: Any) -> None:
        self.data = []

    def process_formdata(self, valuelist: list[str]) -> None:
        self.data = list(valuelist)


async def save_uploaded_file(file: Any, path: str) -> str | None:
    filename = getattr(file, "filename", None)
    if not filename:
        return None
    read_fn = getattr(file, "read", None)
    if not read_fn:
        return None
    contents = await read_fn() if asyncio.iscoroutinefunction(read_fn) else read_fn()
    if not contents:
        return None
    return await save_image(Image(file_bytes=contents, filename=filename), path)


def attach_photo_fields(form_class: type, media_prefix: str) -> type:
    """Subclass the scaffolded form, injecting the existing-photos + upload fields."""

    class PhotoForm(form_class):  # type: ignore[valid-type, misc]
        existing_photos = ExistingPhotosField(
            "Текущие фото (отметьте, чтобы удалить)", media_prefix=media_prefix
        )
        upload_images = MultipleFileField(
            "Добавить фото (можно несколько)", validators=[Optional()]
        )

    return PhotoForm


async def apply_photo_changes(model: Any, data: dict, request: Request, model_class: type, path: str) -> None:
    """Persist deletions, uploads, and reordering of an entity's photos.

    Writes cover (image_url) + remaining (image_urls) on `model_class`, then removes
    orphaned files from disk. Mirrors the reorder contract of _DeletableImagesWidget.
    """
    to_delete = set(data.get("existing_photos") or [])

    files = data.get("upload_images") or []
    if not isinstance(files, list):
        files = [files] if files else []
    saved: list[str] = [n for n in [await save_uploaded_file(f, path) for f in files] if n]

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
        ordered_current = ([model.image_url] if model.image_url else []) + list(model.image_urls or [])

    if not to_delete and not saved and not filenames:
        return

    kept = [fn for fn in ordered_current if fn not in to_delete] + saved
    new_cover = kept[0] if kept else None
    new_image_urls = kept[1:]

    pk_col = model_class.__mapper__.primary_key[0]
    db = container.database()
    async with db.session() as session:
        await session.execute(
            sa_update(model_class)
            .where(pk_col == getattr(model, pk_col.name))
            .values(image_url=new_cover, image_urls=new_image_urls)
        )
        await session.commit()
    model.image_url = new_cover
    model.image_urls = new_image_urls

    for filename in to_delete:
        await delete_image(filename, path)
