from sqlalchemy import select

from src.clients.database.models.promo import Promo
from src.services.base import BaseService
from src.services.promo.interface import PromoServiceI
from src.services.promo.schemas import PromoResponse


class PromoService(BaseService, PromoServiceI):
    async def list_active(self) -> list[PromoResponse]:
        async with self.session() as session:
            result = await session.execute(
                select(Promo).where(Promo.is_active.is_(True)).order_by(Promo.sort_order, Promo.promo_id)
            )
            promos = result.scalars().all()

        out: list[PromoResponse] = []
        for promo in promos:
            frames = ([promo.image_url] if promo.image_url else []) + list(promo.image_urls or [])
            if not frames:
                continue  # a promo with no media isn't shown
            out.append(PromoResponse(promo_id=promo.promo_id, title=promo.title, frames=frames))
        return out
