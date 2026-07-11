from http import HTTPStatus

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse, Response

from src.container import container
from src.server.dependencies import require_telegram_user
from src.services.basket.interface import BasketServiceI
from src.services.basket.schemas import (
    BasketDatesUpdate,
    BasketItemCreate,
    BasketResponse,
    QuantityUpdate,
)
from src.services.static import create_message, delete_message

basket_tag = "Basket"
router = APIRouter(prefix="/basket", tags=[basket_tag])


async def get_basket_service() -> BasketServiceI:
    return container.basket_service()


@router.get("/", response_model=BasketResponse)
async def get_basket(
    user_id: int = Depends(require_telegram_user),
    basket_service: BasketServiceI = Depends(get_basket_service),
) -> BasketResponse:
    return await basket_service.get_user_basket(user_id)


@router.put("/dates", response_model=BasketResponse)
async def set_basket_dates(
    dates: BasketDatesUpdate,
    user_id: int = Depends(require_telegram_user),
    basket_service: BasketServiceI = Depends(get_basket_service),
) -> BasketResponse:
    # Atomically sets the trip window and migrates existing items into it,
    # returning the updated basket.
    return await basket_service.set_dates_and_migrate(user_id, dates)


@router.post("/add_item")
async def add_item(
    item_data: BasketItemCreate,
    user_id: int = Depends(require_telegram_user),
    basket_service: BasketServiceI = Depends(get_basket_service),
) -> JSONResponse:
    await basket_service.add_item(user_id, item_data)
    return JSONResponse(
        content={"message": create_message.format(entity=basket_tag + " item")}, status_code=HTTPStatus.CREATED
    )


@router.delete("/remove_item/{basket_item_id}")
async def remove_item(
    basket_item_id: int,
    user_id: int = Depends(require_telegram_user),
    basket_service: BasketServiceI = Depends(get_basket_service),
) -> JSONResponse:
    await basket_service.remove_item(basket_item_id, user_id)
    return JSONResponse(content={"message": "Item removed from basket"}, status_code=200)


@router.delete("/clear")
async def clear_basket(
    user_id: int = Depends(require_telegram_user),
    basket_service: BasketServiceI = Depends(get_basket_service),
) -> JSONResponse:
    basket = await basket_service.get_user_basket(user_id)
    await basket_service.clear_basket(basket.basket_id, user_id)
    return JSONResponse(content={"message": delete_message.format(entity=basket_tag)}, status_code=200)


@router.post("/change_quantity")
async def change_quantity(
    quantity_update: QuantityUpdate,
    user_id: int = Depends(require_telegram_user),
    basket_service: BasketServiceI = Depends(get_basket_service),
) -> Response:
    await basket_service.change_quantity(quantity_update, user_id)
    return Response(status_code=204)
