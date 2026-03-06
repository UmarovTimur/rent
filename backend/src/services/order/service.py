from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.clients.database.models.basket import BasketItem, Basket
from src.clients.database.models.order import Order, OrderItem
from src.clients.database.models.user import User
from src.services.base import BaseService
from src.services.basket.interface import BasketServiceI
from src.services.errors import OrderNotFoundError, BasketNotFoundError
from src.services.order.interface import OrderServiceI
from src.services.order.schemas import OrderCreate, OrderResponse, OrderStatus, OrderItemResponse
from src.services.rental.interface import RentalServiceI
from src.services.rental_pricing import calculate_rental_line_total


class OrderService(BaseService, OrderServiceI):
    def __init__(
        self,
        session: Callable[..., AsyncSession],
        basket_service: BasketServiceI,
        rental_service: RentalServiceI,
    ) -> None:
        super().__init__(session)
        self.basket_service = basket_service
        self.rental_service = rental_service

    async def create_order(self, user_id: int, order_data: OrderCreate) -> None:
        async with self.session() as session, session.begin():
            query = select(Basket).where(Basket.user_id == user_id).options(
                joinedload(Basket.items).joinedload(BasketItem.product),
            )
            result = await session.execute(query)
            basket = result.unique().scalar_one_or_none()

            if not basket or not basket.items:
                raise BasketNotFoundError

            rental_demands: dict[tuple[int, datetime, datetime], int] = {}
            for basket_item in basket.items:
                if basket_item.rental_start is None:
                    await self.rental_service.ensure_product_available(
                        session=session,
                        product_id=basket_item.product_id,
                        quantity=basket_item.quantity,
                        rental_start=None,
                        rental_end=None,
                    )
                    continue

                demand_key = (
                    basket_item.product_id,
                    basket_item.rental_start,
                    basket_item.rental_end,
                )
                rental_demands[demand_key] = rental_demands.get(demand_key, 0) + basket_item.quantity

            for (product_id, rental_start, rental_end), quantity in rental_demands.items():
                await self.rental_service.ensure_product_available(
                    session=session,
                    product_id=product_id,
                    quantity=quantity,
                    rental_start=rental_start,
                    rental_end=rental_end,
                )

            total_price = await self._calculate_total_price(session, order_data.basket_id)
            new_order = Order(
                user_id=user_id,
                total_price=total_price,
                order_date=datetime.now(tz=UTC),
                **order_data.model_dump(),
            )
            session.add(new_order)
            await session.flush()
            order_id = new_order.order_id

            for basket_item in basket.items:
                order_item = OrderItem(
                    order_id=new_order.order_id,
                    product_id=basket_item.product_id,
                    unit_price=basket_item.product.price,
                    quantity=basket_item.quantity,
                    rental_start=basket_item.rental_start,
                    rental_end=basket_item.rental_end,
                )
                session.add(order_item)

        await self.basket_service.clear_basket(order_data.basket_id)

    async def get_order(self, order_id: int) -> OrderResponse:
        async with self.session() as session:
            query = select(Order).where(Order.order_id == order_id).options(
                joinedload(Order.items).joinedload(OrderItem.product),
            )
            result = await session.execute(query)
            order = result.unique().scalar_one_or_none()

            if not order:
                raise OrderNotFoundError
            return self._to_order_response(order)

    async def get_all(self, user_id: int | None) -> list[OrderResponse]:
        async with self.session() as session:
            query = select(Order).options(
                joinedload(Order.items).joinedload(OrderItem.product),
            )
            if user_id is not None:
                query = query.where(Order.user_id == user_id)
            result = await session.execute(query)
            orders = result.unique().scalars().all()
            return [self._to_order_response(order) for order in orders]

    @staticmethod
    def _to_order_response(order: Order) -> OrderResponse:
        return OrderResponse(
            order_id=order.order_id,
            basket_id=order.basket_id,
            order_date=order.order_date,
            payment_option=order.payment_option,
            total_price=order.total_price,
            comment=order.comment,
            status=order.status,
            first_name=order.first_name,
            address=order.address,
            phone=order.phone,
            discount=order.discount,
            items=[
                OrderItemResponse(
                    order_item_id=item.order_item_id,
                    product_id=item.product_id,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                )
                for item in order.items
            ],
        )


    async def change_status(self, order_id: int, status: OrderStatus) -> None:
        async with self.session() as session:
            order = await session.get(Order, order_id)
            if order:
                if order.status != status.value:
                    order.status = status.value
                    await session.commit()
            else:
                raise OrderNotFoundError

    @staticmethod
    async def _calculate_total_price(session, basket_id: int) -> int:
        query = (
            select(BasketItem)
            .where(BasketItem.basket_id == basket_id)
            .options(joinedload(BasketItem.product))
        )
        result = await session.execute(query)
        items = result.scalars().unique().all()

        total = 0
        for item in items:
            if item.product:
                total += calculate_rental_line_total(
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                )
        return total

    async def earning_points(self, order_id: int):
        async with self.session() as session, session.begin():
            query = select(Order).where(Order.order_id == order_id)
            result = await session.execute(query)
            order: Order = result.scalars().first()

            stmt = (
                update(User)
                .where(User.user_id == order.user_id)
                .values(coins=User.coins + int(order.total_price/10))

            )
            await session.execute(stmt)
