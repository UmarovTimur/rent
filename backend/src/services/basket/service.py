from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.clients.database.models.basket import Basket, BasketItem
from src.clients.database.models.product import Product
from src.services.base import BaseService
from src.services.basket.interface import BasketServiceI
from src.services.basket.schemas import BasketItemCreate, BasketItemResponse, BasketResponse, QuantityUpdate
from src.services.errors import BasketItemNotFoundError, BasketNotFoundError, ProductNotFoundError
from src.services.rental_pricing import calculate_rental_line_total


class BasketService(BaseService, BasketServiceI):
    async def get_user_basket(self, user_id: int) -> BasketResponse:
        async with self.session() as session, session.begin():
            query = select(Basket).where(Basket.user_id == user_id).options(
                joinedload(Basket.items).joinedload(BasketItem.product),
            )
            result = await session.execute(query)
            basket = result.unique().scalar_one_or_none()
            if not basket:
                basket = Basket(user_id=user_id)
                session.add(basket)
                await session.flush()
                return BasketResponse(
                    basket_id=basket.basket_id,
                    user_id=basket.user_id,
                    discount=basket.discount,
                    total_price=0,
                    items=[],
                )

            items = list(basket.items)
            total_price = sum(
                calculate_rental_line_total(
                    # Basket total always uses current product price.
                    unit_price=item.product.price,
                    quantity=item.quantity,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                )
                for item in items
            )

            return BasketResponse(
                basket_id=basket.basket_id,
                user_id=basket.user_id,
                discount=basket.discount,
                total_price=total_price,
                items=[
                    BasketItemResponse(
                        basket_item_id=item.basket_item_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        rental_start=item.rental_start,
                        rental_end=item.rental_end,
                    )
                    for item in items
                ],
            )

    async def add_item(self, user_id: int, item_data: BasketItemCreate) -> None:
        async with self.session() as session, session.begin():
            query = select(Basket).where(Basket.user_id == user_id)
            result = await session.execute(query)
            basket = result.scalar()

            if not basket:
                basket = Basket(user_id=user_id)
                session.add(basket)
                await session.flush()

            if not await session.get(Product, item_data.product_id):
                raise ProductNotFoundError

            existing_item = await self._get_existing_item(session, basket, item_data)

            if existing_item:
                existing_item.quantity += item_data.quantity
            else:
                new_item = BasketItem(
                    basket_id=basket.basket_id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    rental_start=item_data.rental_start,
                    rental_end=item_data.rental_end,
                )
                session.add(new_item)
                await session.flush()

    @staticmethod
    async def _get_existing_item(session, basket: Basket, item_data: BasketItemCreate):
        query = (
            select(BasketItem)
            .where(
                BasketItem.basket_id == basket.basket_id,
                BasketItem.product_id == item_data.product_id,
            )
        )
        result = await session.execute(query)
        candidates = result.scalars().unique().all()

        for candidate in candidates:
            same_rental_window = (
                candidate.rental_start == item_data.rental_start and candidate.rental_end == item_data.rental_end
            )
            if same_rental_window:
                return candidate

        return None

    async def remove_item(self, basket_item_id: int) -> None:
        async with self.session() as session, session.begin():
            query = select(BasketItem).where(BasketItem.basket_item_id == basket_item_id)
            result = await session.execute(query)
            item = result.scalar()

            if not item:
                raise BasketItemNotFoundError

            await session.delete(item)

    async def clear_basket(self, basket_id: int) -> None:
        async with self.session() as session, session.begin():
            query = select(BasketItem).where(BasketItem.basket_id == basket_id)
            result = await session.execute(query)
            items_to_delete = result.scalars().unique().all()

            if not items_to_delete:
                raise BasketNotFoundError

            for item in items_to_delete:
                await session.delete(item)

    async def change_quantity(self, quantity_update: QuantityUpdate) -> None:
        async with self.session() as session, session.begin():
            query = select(BasketItem).where(BasketItem.basket_item_id == quantity_update.basket_item_id)
            result = await session.execute(query)
            item = result.scalar()

            if not item:
                raise BasketItemNotFoundError

            item.quantity = quantity_update.quantity
