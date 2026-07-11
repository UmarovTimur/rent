from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
from src.services.rental.interface import RentalServiceI
from src.services.rental_pricing import (
    floor_to_step,
    line_half_day_units,
)
from src.settings.billing import BillingSettings


class BasketService(BaseService, BasketServiceI):
    def __init__(
        self,
        session: Callable[..., AsyncSession],
        rental_service: RentalServiceI,
    ) -> None:
        super().__init__(session)
        self.rental_service = rental_service
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

    async def set_dates_and_migrate(self, user_id: int, dates: BasketDatesUpdate) -> BasketResponse:
        """Set the basket trip window and move every item into it, atomically.

        Replaces the old client-side reconciliation (add-then-remove loops that
        raced with manual edits). In one transaction we update the window and, per
        product + add-on group, consolidate all lines into a single line in the new
        window — capped by the product's availability there (dropped if it no longer
        fits). Non-rental lines (no window) are left untouched.
        """
        async with self.session() as session, session.begin():
            query = (
                select(Basket)
                .where(Basket.user_id == user_id)
                .options(selectinload(Basket.items).selectinload(BasketItem.addon_items))
            )
            result = await session.execute(query)
            basket = result.unique().scalar_one_or_none()

            if not basket:
                basket = Basket(user_id=user_id)
                session.add(basket)
                await session.flush()

            basket.rental_start = dates.rental_start
            basket.rental_end = dates.rental_end

            parents = [item for item in basket.items if item.parent_basket_item_id is None]

            # Group by product + its add-on set so lines with different add-ons stay
            # distinct; a group is migrated only if some line is outside the window.
            groups: dict[tuple[int, frozenset[int]], list[BasketItem]] = {}
            for parent in parents:
                if parent.rental_start is None or parent.rental_end is None:
                    continue  # non-rental line, not date-bound
                key = (parent.product_id, frozenset(addon.product_id for addon in parent.addon_items))
                groups.setdefault(key, []).append(parent)

            for (product_id, _addon_key), items in groups.items():
                stale = [
                    item
                    for item in items
                    if item.rental_start != dates.rental_start or item.rental_end != dates.rental_end
                ]
                if not stale:
                    continue

                total_quantity = sum(item.quantity for item in items)
                addon_quantities: dict[int, int] = {}
                for item in items:
                    for addon in item.addon_items:
                        addon_quantities[addon.product_id] = (
                            addon_quantities.get(addon.product_id, 0) + addon.quantity
                        )

                cap = await self.rental_service.available_quantity_for_window(
                    session, product_id, dates.rental_start, dates.rental_end
                )
                limit = 99 if cap is None else min(cap, 99)
                target_quantity = min(total_quantity, limit)

                for item in items:
                    await session.delete(item)  # cascades to add-on children
                await session.flush()

                if target_quantity <= 0:
                    continue

                new_parent = BasketItem(
                    basket_id=basket.basket_id,
                    product_id=product_id,
                    quantity=target_quantity,
                    rental_start=dates.rental_start,
                    rental_end=dates.rental_end,
                )
                session.add(new_parent)
                await session.flush()

                for addon_product_id, addon_quantity in addon_quantities.items():
                    session.add(
                        BasketItem(
                            basket_id=basket.basket_id,
                            product_id=addon_product_id,
                            quantity=addon_quantity,
                            rental_start=dates.rental_start,
                            rental_end=dates.rental_end,
                            parent_basket_item_id=new_parent.basket_item_id,
                        )
                    )
                await session.flush()

        return await self.get_user_basket(user_id)

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

    async def remove_item(self, basket_item_id: int, user_id: int) -> None:
        async with self.session() as session, session.begin():
            item = await self._get_owned_item(session, basket_item_id, user_id)
            await session.delete(item)

    async def clear_basket(self, basket_id: int, user_id: int) -> None:
        async with self.session() as session, session.begin():
            basket = await session.get(Basket, basket_id)
            if not basket or basket.user_id != user_id:
                raise BasketNotFoundError

            query = select(BasketItem).where(BasketItem.basket_id == basket_id)
            result = await session.execute(query)
            items = result.scalars().unique().all()

            # Delete only parent lines — child add-ons cascade (relationship
            # delete-orphan + FK ondelete=CASCADE) — to avoid double-deletes.
            for item in items:
                if item.parent_basket_item_id is None:
                    await session.delete(item)

    async def change_quantity(self, quantity_update: QuantityUpdate, user_id: int) -> None:
        async with self.session() as session, session.begin():
            item = await self._get_owned_item(session, quantity_update.basket_item_id, user_id)
            # Add-ons keep their own quantity (kit components / opt-in add-ons are
            # edited independently) — only the line itself changes here.
            item.quantity = quantity_update.quantity

    @staticmethod
    async def _get_owned_item(session, basket_item_id: int, user_id: int) -> BasketItem:
        """Load a basket item and assert it belongs to `user_id`.

        Raises BasketItemNotFoundError both when the item is missing and when it
        belongs to another user, so ownership is never leaked.
        """
        query = (
            select(BasketItem)
            .where(BasketItem.basket_item_id == basket_item_id)
            .options(joinedload(BasketItem.basket))
        )
        result = await session.execute(query)
        item = result.unique().scalar_one_or_none()
        if not item or item.basket is None or item.basket.user_id != user_id:
            raise BasketItemNotFoundError
        return item
