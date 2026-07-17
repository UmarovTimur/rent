from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from starlette.requests import Request

from src.admin.photo_form import apply_photo_changes, attach_photo_fields, img_tag
from src.clients.database.models.promo import Promo
from src.services.static import promos_path
from src.services.utils import delete_image

_MEDIA = "/media/promos/"


class PromoAdmin(ModelView, model=Promo):
    """Story-style promo banners. Each promo holds an ordered set of photos (cover
    first) managed with the shared multi-photo widget; video support is planned."""

    name = "Promo"
    name_plural = "Promos"
    icon = "fa-solid fa-bullhorn"

    column_list = [Promo.promo_id, Promo.title, Promo.is_active, Promo.sort_order, Promo.image_url]
    column_labels = {
        Promo.title: "Название (внутреннее)",
        Promo.is_active: "Активно",
        Promo.sort_order: "Порядок",
        Promo.image_url: "Обложка",
    }
    column_searchable_list = [Promo.title]
    column_sortable_list = [Promo.sort_order, Promo.promo_id, Promo.is_active]
    form_columns = [Promo.title, Promo.is_active, Promo.sort_order]
    form_widget_args = {"sort_order": {"step": 1, "min": 0}}
    column_formatters = {
        Promo.image_url: lambda m, a: Markup(img_tag(m.image_url, _MEDIA)) if m.image_url else "—",
    }

    async def scaffold_form(self, rules=None):
        return attach_photo_fields(await super().scaffold_form(rules), _MEDIA)

    async def after_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        await apply_photo_changes(model, data, request, Promo, promos_path)

    async def on_model_delete(self, model: Any, request: Request) -> None:
        for filename in [model.image_url] + list(model.image_urls or []):
            if filename:
                await delete_image(filename, promos_path)
