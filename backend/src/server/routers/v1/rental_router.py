from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.container import container
from src.services.rental.interface import RentalServiceI
from src.services.rental.schemas import ProductRentalCalendarResponse

rental_tag = "Rental"
router = APIRouter(prefix="/rental", tags=[rental_tag])


async def get_rental_service() -> RentalServiceI:
    return container.rental_service()


@router.get("/product/{product_id}/calendar", response_model=ProductRentalCalendarResponse)
async def get_product_calendar(
    product_id: int,
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    slot_minutes: int | None = Query(None, ge=1),
    rental_service: RentalServiceI = Depends(get_rental_service),
) -> ProductRentalCalendarResponse:
    return await rental_service.get_product_calendar(
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        slot_minutes=slot_minutes,
    )
