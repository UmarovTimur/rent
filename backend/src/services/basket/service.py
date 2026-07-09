from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from src.clients.database.models.basket import Basket, BasketItem
from src.clients.database.models.product import Product, product_addon_links
from src.services.base import BaseService
from src.services.basket.interface import BasketServiceI
from src.services.basket.schemas import (
    AddonSelection,
    BasketDatesUpdate,
    BasketItemAddonResponse,
    BasketItemCreate,
    BasketItemResponse,
    BasketResponse,
    QuantityUpdate,
)
from src.services.errors import BasketItemNotFoundError, BasketNotFoundError, ProductNotFoundError
from src.services.rental_pricing import (
    floor_to_step,
    line_half_day_units,
)
from src.settings.billing import BillingSettings


class BasketService(BaseService, BasketServiceI):
    async def get_user_basket(self, user_id: int) -> BasketResponse:
        async with self.session() as session, session.begin():
            query = select(Basket).where(Basket.user_id == user_id).options(
                selectinload(Basket.items).joinedload(BasketItem.product),
                selectinload(Basket.items)
                .selectinload(BasketItem.addon_items)
                .joinedload(BasketItem.product),
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
                    rental_start=basket.rental_start,
                    rental_end=basket.rental_end,
                    total_price=0,
                    items=[],
                )

            all_items = list(basket.items)
            # Total over ALL lines (parent products + child add-ons), honouring
            # each product's price_mode. Sum half-day units, divide once, floor once.
            total_units = sum(
                line_half_day_units(
                    unit_price=item.product.price,  # basket always uses current price
                    quantity=item.quantity,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                    price_mode=item.product.price_mode,
                )
                for item in all_items
            )
            total_price = floor_to_step(
                total_units // 2, BillingSettings().total_floor_step
            )

            parents = [i for i in all_items if i.parent_basket_item_id is None]

            return BasketResponse(
                basket_id=basket.basket_id,
                user_id=basket.user_id,
                discount=basket.discount,
                rental_start=basket.rental_start,
                rental_end=basket.rental_end,
                total_price=total_price,
                items=[
                    BasketItemResponse(
                        basket_item_id=item.basket_item_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        rental_start=item.rental_start,
                        rental_end=item.rental_end,
                        addons=[
                            BasketItemAddonResponse(
                                basket_item_id=addon.basket_item_id,
                                product_id=addon.product_id,
                                name=addon.product.name,
                                price=addon.product.price,
                                price_mode=addon.product.price_mode,
                                quantity=addon.quantity,
                            )
                            for addon in item.addon_items
                        ],
                    )
                    for item in parents
                ],
            )

    async def set_basket_dates(self, user_id: int, dates: BasketDatesUpdate) -> None:
        async with self.session() as session, session.begin():
            query = select(Basket).where(Basket.user_id == user_id)
            result = await session.execute(query)
            basket = result.scalar()

            if not basket:
                basket = Basket(user_id=user_id)
                session.add(basket)

            basket.rental_start = dates.rental_start
            basket.rental_end = dates.rental_end

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

            valid_addons = await self._validate_addons(
                session, item_data.product_id, item_data.addons
            )
            addon_ids = [a.product_id for a in valid_addons]

            existing_item = await self._get_existing_item(session, basket, item_data, addon_ids)

            if existing_item:
                existing_item.quantity += item_data.quantity
                # Add-ons keep their own quantity, added on top of what's there.
                qty_by_product = {a.product_id: a.quantity for a in valid_addons}
                for addon in existing_item.addon_items:
                    addon.quantity += qty_by_product.get(addon.product_id, 0)
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

                for addon in valid_addons:
                    session.add(
                        BasketItem(
                            basket_id=basket.basket_id,
                            product_id=addon.product_id,
                            quantity=addon.quantity,  # add-on's own quantity
                            rental_start=item_data.rental_start,
                            rental_end=item_data.rental_end,
                            parent_basket_item_id=new_item.basket_item_id,
                        )
                    )
                await session.flush()

    @staticmethod
    async def _validate_addons(session, product_id: int, addons: list[AddonSelection]) -> list[AddonSelection]:
        """Keep only add-ons that are real, is_addon, and linked to this parent.
        De-dupes by product_id while preserving order."""
        if not addons:
            return []

        result = await session.execute(
            select(product_addon_links.c.addon_product_id).where(
                product_addon_links.c.parent_product_id == product_id
            )
        )
        allowed = set(result.scalars().all())

        seen: set[int] = set()
        valid: list[AddonSelection] = []
        for addon in addons:
            if addon.product_id in allowed and addon.product_id not in seen:
                seen.add(addon.product_id)
                valid.append(addon)
        return valid

    @staticmethod
    async def _get_existing_item(
        session, basket: Basket, item_data: BasketItemCreate, addon_ids: list[int]
    ):
        query = (
            select(BasketItem)
            .where(
                BasketItem.basket_id == basket.basket_id,
                BasketItem.product_id == item_data.product_id,
                BasketItem.parent_basket_item_id.is_(None),
            )
            .options(selectinload(BasketItem.addon_items))
        )
        result = await session.execute(query)
        candidates = result.scalars().unique().all()

        target_addons = set(addon_ids)
        for candidate in candidates:
            same_rental_window = (
                candidate.rental_start == item_data.rental_start
                and candidate.rental_end == item_data.rental_end
            )
            same_addons = {a.product_id for a in candidate.addon_items} == target_addons
            if same_rental_window and same_addons:
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
            items = result.scalars().unique().all()

            if not items:
                raise BasketNotFoundError

            # Delete only parent lines — child add-ons cascade (relationship
            # delete-orphan + FK ondelete=CASCADE) — to avoid double-deletes.
            for item in items:
                if item.parent_basket_item_id is None:
                    await session.delete(item)

    async def change_quantity(self, quantity_update: QuantityUpdate) -> None:
        async with self.session() as session, session.begin():
            query = select(BasketItem).where(
                BasketItem.basket_item_id == quantity_update.basket_item_id
            )
            result = await session.execute(query)
            item = result.scalar()

            if not item:
                raise BasketItemNotFoundError

            # Add-ons keep their own quantity (kit components / opt-in add-ons are
            # edited independently) — only the line itself changes here.
            item.quantity = quantity_update.quantity
