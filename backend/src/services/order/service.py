from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.clients.database.models.basket import BasketItem, Basket
from src.clients.database.models.order import Order, OrderItem
from src.clients.database.models.user import User
from src.services.base import BaseService
from src.services.basket.interface import BasketServiceI
from src.services.errors import OrderNotFoundError, BasketNotFoundError, TooManyActiveOrdersError, UserBannedError
from src.services.order.interface import OrderServiceI
from src.services.order.schemas import OrderCreate, OrderResponse, OrderStatus, OrderItemResponse
from src.services.rental.interface import RentalServiceI
from src.services.rental_pricing import (
    floor_to_step,
    line_half_day_units,
)
from src.settings.billing import BillingSettings

# Caps how many orders a single user can have open at once (created/in_progress/
# taken/paused — anything not yet returned/completed/canceled), so one user can't
# mass-hold inventory across many orders. Deliberately not configurable via env —
# bump this constant directly if it ever needs to change.
MAX_ACTIVE_ORDERS_PER_USER = 3
_ACTIVE_ORDER_STATUSES = (
    OrderStatus.CREATED.value,
    OrderStatus.IN_PROGRESS.value,
    OrderStatus.TAKEN.value,
    OrderStatus.PAUSED.value,
)


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

    async def create_order(self, user_id: int, order_data: OrderCreate) -> int:
        async with self.session() as session, session.begin():
            # Step 1 — lock the user's basket ROW ALONE (no join). This
            # serializes concurrent create_order calls from the same user (they
            # contend on this row), fixing two races at once: the active-order
            # cap TOCTOU (count-then-insert) and one basket spawning duplicate
            # orders. Crucially the join is NOT here: under READ COMMITTED a
            # `FOR UPDATE` that includes a join re-reads the locked row after the
            # wait but keeps the joined rows from the pre-wait snapshot, so a
            # blocked second caller would still see the just-deleted basket items.
            basket = (
                await session.execute(
                    select(Basket).where(Basket.user_id == user_id).with_for_update()
                )
            ).scalar_one_or_none()
            if not basket:
                raise BasketNotFoundError

            # Step 2 — load the items in a SEPARATE query, which runs at a fresh
            # statement snapshot once the lock is held, so a serialized caller
            # correctly sees an empty basket if the prior order already cleared it.
            items_result = await session.execute(
                select(BasketItem)
                .where(BasketItem.basket_id == basket.basket_id)
                .options(joinedload(BasketItem.product))
            )
            basket_items = items_result.scalars().unique().all()
            if not basket_items:
                raise BasketNotFoundError

            is_admin, is_banned, coins = (
                await session.execute(
                    select(User.is_admin, User.is_banned, User.coins).where(User.user_id == user_id)
                )
            ).one()
            if is_banned:
                raise UserBannedError

            # Admins place orders on behalf of phone-in clients too, so they
            # legitimately carry more concurrent active orders than a regular
            # customer — the cap only protects against one client hoarding
            # inventory, not against normal admin usage.
            if not is_admin:
                active_orders_count = await session.scalar(
                    select(func.count())
                    .select_from(Order)
                    .where(Order.user_id == user_id, Order.status.in_(_ACTIVE_ORDER_STATUSES))
                )
                if active_orders_count >= MAX_ACTIVE_ORDERS_PER_USER:
                    raise TooManyActiveOrdersError

            rental_demands: dict[tuple[int, datetime, datetime], int] = {}
            for basket_item in basket_items:
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

            # Always price/attach the authenticated user's own basket — never a
            # client-supplied basket_id (which could point at another user).
            # Build the Order explicitly from a whitelist of client fields —
            # never spread order_data.model_dump(), which would let a client set
            # status/discount (status="taken" bypasses payment/approval).
            total_price = await self._calculate_total_price(session, basket.basket_id)

            # Redeem bonus coins as a discount, capped at the user's own balance
            # and at the order total (never goes negative). The client only
            # toggles use_coins — the amount is always computed server-side.
            coins_redeemed = 0
            if order_data.use_coins and coins:
                coins_redeemed = min(int(coins), total_price)
                if coins_redeemed > 0:
                    await session.execute(
                        update(User)
                        .where(User.user_id == user_id)
                        .values(coins=User.coins - coins_redeemed)
                    )
                    total_price -= coins_redeemed

            order_date = datetime.now(tz=UTC)
            payment_hold_minutes = BillingSettings().payment_hold_minutes
            new_order = Order(
                user_id=user_id,
                basket_id=basket.basket_id,
                total_price=total_price,
                discount=float(coins_redeemed) if coins_redeemed else None,
                order_date=order_date,
                payment_deadline=order_date + timedelta(minutes=payment_hold_minutes),
                status=OrderStatus.CREATED.value,
                payment_option=order_data.payment_option,
                comment=order_data.comment,
                first_name=order_data.first_name,
                address=order_data.address,
                phone=order_data.phone,
            )
            session.add(new_order)
            await session.flush()
            order_id = new_order.order_id

            # Pass 1: create an OrderItem per basket line, remembering the
            # basket_item_id → OrderItem mapping (parent ids exist only after flush).
            order_item_by_basket_id: dict[int, OrderItem] = {}
            for basket_item in basket_items:
                order_item = OrderItem(
                    order_id=new_order.order_id,
                    product_id=basket_item.product_id,
                    unit_price=basket_item.product.price,
                    quantity=basket_item.quantity,
                    rental_start=basket_item.rental_start,
                    rental_end=basket_item.rental_end,
                )
                session.add(order_item)
                order_item_by_basket_id[basket_item.basket_item_id] = order_item

            await session.flush()

            # Pass 2: link add-on OrderItems to their parent's OrderItem.
            for basket_item in basket_items:
                if basket_item.parent_basket_item_id is None:
                    continue
                child = order_item_by_basket_id[basket_item.basket_item_id]
                parent = order_item_by_basket_id.get(basket_item.parent_basket_item_id)
                if parent is not None:
                    child.parent_order_item_id = parent.order_item_id

            # Clear the basket INSIDE this locked transaction (not after commit):
            # otherwise a second concurrent create_order, after acquiring the
            # basket lock this one just released, would still see the un-cleared
            # items and produce a duplicate order. Delete only parent lines —
            # child add-ons cascade (delete-orphan + FK ondelete=CASCADE).
            for basket_item in basket_items:
                if basket_item.parent_basket_item_id is None:
                    await session.delete(basket_item)
        return order_id

    async def get_order(self, order_id: int) -> OrderResponse:
        async with self.session() as session:
            query = select(Order).where(Order.order_id == order_id).options(
                joinedload(Order.items).joinedload(OrderItem.product),
            )
            result = await session.execute(query)
            order = result.unique().scalar_one_or_none()

            if not order:
                raise OrderNotFoundError
            username = await session.scalar(select(User.username).where(User.user_id == order.user_id))
            return self._to_order_response(order, username)

    async def get_all(self, user_id: int | None) -> list[OrderResponse]:
        async with self.session() as session:
            query = select(Order).options(
                joinedload(Order.items).joinedload(OrderItem.product),
            )
            if user_id is not None:
                query = query.where(Order.user_id == user_id)
            result = await session.execute(query)
            orders = result.unique().scalars().all()

            # One query for all usernames, mapped by user_id (avoids N+1).
            user_ids = {o.user_id for o in orders}
            usernames: dict[int, str | None] = {}
            if user_ids:
                rows = await session.execute(
                    select(User.user_id, User.username).where(User.user_id.in_(user_ids))
                )
                usernames = {uid: uname for uid, uname in rows}
            return [self._to_order_response(order, usernames.get(order.user_id)) for order in orders]

    @staticmethod
    def _to_order_response(order: Order, username: str | None = None) -> OrderResponse:
        return OrderResponse(
            order_id=order.order_id,
            user_id=order.user_id,
            username=username,
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
                    product_name=item.product.name if item.product else None,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                    parent_order_item_id=item.parent_order_item_id,
                )
                for item in order.items
            ],
        )


    async def change_status(self, order_id: int, status: OrderStatus) -> None:
        # Delegates to RentalService, the single choke point that validates the
        # status-transition state machine and (for created -> in_progress/taken)
        # re-checks availability before committing — see update_rental_status.
        await self.rental_service.update_rental_status(order_id, status)

    @staticmethod
    async def _calculate_total_price(session, basket_id: int) -> int:
        query = (
            select(BasketItem)
            .where(BasketItem.basket_id == basket_id)
            .options(joinedload(BasketItem.product))
        )
        result = await session.execute(query)
        items = result.scalars().unique().all()

        # Sum half-day units across lines, divide once, floor once — see
        # rental_pricing.py for why (odd-price half-day losses don't accumulate).
        total_units = 0
        for item in items:
            if item.product:
                total_units += line_half_day_units(
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                    price_mode=item.product.price_mode,
                )
        return floor_to_step(total_units // 2, BillingSettings().total_floor_step)
