from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database.models.order import Order, OrderItem
from src.clients.database.models.rental import ProductRental, ProductRentalSlot
from src.services.base import BaseService
from src.services.errors import (
    InvalidRentalPeriodError,
    RentalConfigNotFoundError,
    RentalUnavailableError,
)
from src.services.order.schemas import OrderStatus
from src.services.rental.interface import RentalServiceI
from src.services.rental.schemas import ProductRentalCalendarResponse, ProductRentalCalendarSlot


@dataclass(slots=True)
class _ReservationInterval:
    start: datetime
    end: datetime
    quantity: int


class RentalService(BaseService, RentalServiceI):
    def __init__(self, session: Callable[..., AsyncSession]) -> None:
        super().__init__(session)

    async def get_product_calendar(
        self,
        product_id: int,
        date_from: datetime,
        date_to: datetime,
        slot_minutes: int | None = None,
    ) -> ProductRentalCalendarResponse:
        self._validate_period(date_from, date_to)

        async with self.session() as session:
            rental = await self._get_product_rental(session, product_id)
            manual_slots = await self._get_manual_slots(session, rental.rental_id, date_from, date_to)
            order_intervals = await self._get_order_reservations(session, product_id, date_from, date_to)

            slot_size = slot_minutes or rental.slot_duration_minutes
            if slot_size <= 0:
                raise InvalidRentalPeriodError("slot_minutes must be positive")

            slots = []
            for slot_start, slot_end in self._iter_slots(date_from, date_to, slot_size):
                manual_state = self._manual_state_for_window(manual_slots, slot_start, slot_end, rental.total_quantity)
                order_reserved = self._peak_reserved_quantity(order_intervals, slot_start, slot_end)

                if manual_state["is_closed"]:
                    available = 0
                else:
                    available = max(
                        0,
                        manual_state["effective_capacity"]
                        - manual_state["manual_reserved_quantity"]
                        - manual_state["blocked_quantity"]
                        - order_reserved,
                    )

                slots.append(
                    ProductRentalCalendarSlot(
                        slot_start=slot_start,
                        slot_end=slot_end,
                        effective_capacity=manual_state["effective_capacity"],
                        order_reserved_quantity=order_reserved,
                        manual_reserved_quantity=manual_state["manual_reserved_quantity"],
                        blocked_quantity=manual_state["blocked_quantity"],
                        available_quantity=available,
                        is_closed=manual_state["is_closed"],
                        is_available=available > 0,
                    )
                )

            return ProductRentalCalendarResponse(
                product_id=product_id,
                rental_id=rental.rental_id,
                total_quantity=rental.total_quantity,
                slot_duration_minutes=rental.slot_duration_minutes,
                range_start=date_from,
                range_end=date_to,
                slots=slots,
            )

    async def ensure_product_available(
        self,
        session: AsyncSession,
        product_id: int,
        quantity: int,
        rental_start: datetime | None,
        rental_end: datetime | None,
    ) -> None:
        if quantity <= 0:
            raise RentalUnavailableError("Quantity must be positive")

        rental = await self._get_product_rental(session, product_id, for_update=True, allow_missing=True)

        # Non-rental products are always available for regular ordering; rental dates are not accepted for them.
        if not rental or not rental.is_enabled:
            if rental_start is not None or rental_end is not None:
                raise RentalConfigNotFoundError("Rental dates were provided for a non-rentable product")
            return

        if (rental_start is None) != (rental_end is None):
            raise InvalidRentalPeriodError("rental_start and rental_end must be provided together")
        if rental_start is None or rental_end is None:
            raise InvalidRentalPeriodError("Rental dates are required for rentable product")
        self._validate_period(rental_start, rental_end)

        manual_slots = await self._get_manual_slots(session, rental.rental_id, rental_start, rental_end)
        order_intervals = await self._get_order_reservations(session, product_id, rental_start, rental_end)

        for slot_start, slot_end in self._iter_slots(rental_start, rental_end, rental.slot_duration_minutes):
            manual_state = self._manual_state_for_window(manual_slots, slot_start, slot_end, rental.total_quantity)
            if manual_state["is_closed"]:
                raise RentalUnavailableError("Rental slot is closed")

            order_reserved = self._peak_reserved_quantity(order_intervals, slot_start, slot_end)
            available = (
                manual_state["effective_capacity"]
                - manual_state["manual_reserved_quantity"]
                - manual_state["blocked_quantity"]
                - order_reserved
            )
            if available < quantity:
                raise RentalUnavailableError(
                    f"Not enough quantity for rental window {slot_start.isoformat()} - {slot_end.isoformat()}"
                )

    async def _get_product_rental(
        self,
        session: AsyncSession,
        product_id: int,
        *,
        for_update: bool = False,
        allow_missing: bool = False,
    ) -> ProductRental | None:
        stmt = select(ProductRental).where(ProductRental.product_id == product_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await session.execute(stmt)
        rental = result.scalar_one_or_none()
        if not rental and not allow_missing:
            raise RentalConfigNotFoundError
        return rental

    async def _get_manual_slots(
        self,
        session: AsyncSession,
        rental_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[ProductRentalSlot]:
        stmt = (
            select(ProductRentalSlot)
            .where(
                ProductRentalSlot.rental_id == rental_id,
                ProductRentalSlot.slot_start < date_to,
                ProductRentalSlot.slot_end > date_from,
            )
            .order_by(ProductRentalSlot.slot_start, ProductRentalSlot.slot_end)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _get_order_reservations(
        self,
        session: AsyncSession,
        product_id: int,
        date_from: datetime,
        date_to: datetime,
    ) -> list[_ReservationInterval]:
        stmt = (
            select(
                OrderItem.rental_start,
                OrderItem.rental_end,
                func.sum(OrderItem.quantity).label("reserved_quantity"),
            )
            .join(Order, Order.order_id == OrderItem.order_id)
            .where(
                OrderItem.product_id == product_id,
                OrderItem.rental_start.is_not(None),
                OrderItem.rental_end.is_not(None),
                OrderItem.rental_start < date_to,
                OrderItem.rental_end > date_from,
                Order.status != OrderStatus.CANCELED.value,
            )
            .group_by(OrderItem.rental_start, OrderItem.rental_end)
        )
        result = await session.execute(stmt)
        return [
            _ReservationInterval(start=row.rental_start, end=row.rental_end, quantity=int(row.reserved_quantity or 0))
            for row in result.all()
        ]

    @staticmethod
    def _iter_slots(date_from: datetime, date_to: datetime, slot_minutes: int):
        step = timedelta(minutes=slot_minutes)
        current = date_from
        while current < date_to:
            slot_end = min(current + step, date_to)
            yield current, slot_end
            current = slot_end

    @staticmethod
    def _peak_reserved_quantity(
        intervals: list[_ReservationInterval],
        slot_start: datetime,
        slot_end: datetime,
    ) -> int:
        events: list[tuple[datetime, int]] = []
        for interval in intervals:
            start = max(interval.start, slot_start)
            end = min(interval.end, slot_end)
            if end <= start:
                continue
            events.append((start, interval.quantity))
            events.append((end, -interval.quantity))

        if not events:
            return 0

        # End events first on identical timestamps to avoid inflating concurrency on boundaries.
        events.sort(key=lambda x: (x[0], 0 if x[1] < 0 else 1))
        current = 0
        peak = 0
        for _, delta in events:
            current += delta
            peak = max(peak, current)
        return peak

    @staticmethod
    def _manual_state_for_window(
        manual_slots: list[ProductRentalSlot],
        slot_start: datetime,
        slot_end: datetime,
        default_capacity: int,
    ) -> dict[str, int | bool]:
        overlapping = [slot for slot in manual_slots if slot.slot_start < slot_end and slot.slot_end > slot_start]

        is_closed = any(slot.is_closed for slot in overlapping)
        capacity_overrides = [slot.capacity_override for slot in overlapping if slot.capacity_override is not None]
        effective_capacity = min(capacity_overrides) if capacity_overrides else default_capacity
        blocked_quantity = sum(slot.blocked_quantity for slot in overlapping)
        manual_reserved_quantity = sum(slot.reserved_quantity for slot in overlapping)

        return {
            "is_closed": is_closed,
            "effective_capacity": max(0, effective_capacity),
            "blocked_quantity": max(0, blocked_quantity),
            "manual_reserved_quantity": max(0, manual_reserved_quantity),
        }

    @staticmethod
    def _validate_period(date_from: datetime, date_to: datetime) -> None:
        if date_to <= date_from:
            raise InvalidRentalPeriodError("date_to must be later than date_from")
