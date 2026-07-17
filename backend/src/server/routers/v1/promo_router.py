from fastapi import APIRouter, Depends

from src.container import container
from src.services.promo.interface import PromoServiceI
from src.services.promo.schemas import PromoResponse

router = APIRouter(prefix="/promos", tags=["Promo"])


async def get_promo_service() -> PromoServiceI:
    return container.promo_service()


@router.get("/", response_model=list[PromoResponse])
async def list_promos(
    promo_service: PromoServiceI = Depends(get_promo_service),
) -> list[PromoResponse]:
    # Public content (like the catalog) — no auth required.
    return await promo_service.list_active()
