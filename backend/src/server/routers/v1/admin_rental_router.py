from datetime import datetime
from http import HTTPStatus

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response

from src.container import container
from src.server.dependencies import require_admin
from src.services.bot_notification import notify_status_changed
from src.services.order.schemas import OrderStatus
from src.services.rental.interface import RentalServiceI
from src.services.rental.schemas import RentalOrderDetail, RentalOrderSummary, RentalStatusUpdate

admin_rental_tag = "Admin Rentals"
router = APIRouter(prefix="/admin", tags=[admin_rental_tag])


async def get_rental_service() -> RentalServiceI:
    return container.rental_service()


@router.get("/rentals", response_model=list[RentalOrderSummary], dependencies=[Depends(require_admin)])
async def list_rentals(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    status: OrderStatus | None = Query(None),
    rental_service: RentalServiceI = Depends(get_rental_service),
) -> list[RentalOrderSummary]:
    return await rental_service.list_admin_rentals(date_from=date_from, date_to=date_to, status=status)


@router.get("/rentals/{order_id}", response_model=RentalOrderDetail, dependencies=[Depends(require_admin)])
async def get_rental(
    order_id: int,
    rental_service: RentalServiceI = Depends(get_rental_service),
) -> RentalOrderDetail:
    return await rental_service.get_admin_rental(order_id)


@router.patch("/rentals/{order_id}/status", dependencies=[Depends(require_admin)])
async def update_rental_status(
    order_id: int,
    status_update: RentalStatusUpdate,
    background_tasks: BackgroundTasks,
    rental_service: RentalServiceI = Depends(get_rental_service),
) -> Response:
    await rental_service.update_rental_status(order_id, status_update.status)
    background_tasks.add_task(notify_status_changed, order_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)
