from http import HTTPStatus

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from starlette.responses import JSONResponse

from src.container import container
from src.server.dependencies import Caller, require_telegram_user, require_user_or_internal
from src.services.bot_notification import notify_client_order_created, notify_new_order
from src.services.calendar_sync import sync_order_calendar
from src.services.order.interface import OrderServiceI
from src.services.order.schemas import OrderCreate, OrderResponse, OrderStatus
from src.services.static import create_message

order_tag = "Order"
router = APIRouter(prefix="/order", tags=[order_tag])


async def get_order_service() -> OrderServiceI:
    return container.order_service()


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(require_telegram_user),
    order_service: OrderServiceI = Depends(get_order_service),
) -> JSONResponse:
    order_id = await order_service.create_order(user_id=user_id, order_data=order_data)
    background_tasks.add_task(notify_new_order, order_id)
    background_tasks.add_task(notify_client_order_created, order_id)
    return JSONResponse(content={"message": create_message.format(entity=order_tag)}, status_code=HTTPStatus.CREATED)


@router.get("/", response_model=list[OrderResponse])
async def get_all(
    user_id: int | None = Query(None),
    caller: Caller = Depends(require_user_or_internal),
    order_service: OrderServiceI = Depends(get_order_service),
) -> list[OrderResponse]:
    # Telegram users only ever see their own orders; the bot (internal) may query
    # a specific user or all orders for admin views.
    if caller.is_internal:
        return await order_service.get_all(user_id)
    return await order_service.get_all(caller.user_id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    caller: Caller = Depends(require_user_or_internal),
    order_service: OrderServiceI = Depends(get_order_service),
) -> OrderResponse:
    order = await order_service.get_order(order_id)
    caller.authorize_user(order.user_id)
    return order


@router.patch("/change_status/{order_id}")
async def change_status(
    order_id: int,
    status: OrderStatus,
    background_tasks: BackgroundTasks,
    caller: Caller = Depends(require_user_or_internal),
    order_service: OrderServiceI = Depends(get_order_service),
) -> Response:
    # The bot (internal) may drive any transition; a Telegram user may only
    # cancel their own order.
    if not caller.is_internal:
        order = await order_service.get_order(order_id)
        caller.authorize_user(order.user_id)
        if status != OrderStatus.CANCELED:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="You may only cancel your own order")
    await order_service.change_status(order_id, status)
    background_tasks.add_task(sync_order_calendar, order_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)
