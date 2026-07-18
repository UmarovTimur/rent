from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.clients.database.models.order import Order, OrderItem
from src.clients.database.models.rental import ProductRental, ProductRentalSlot
from src.clients.database.models.user import User
from src.services.base import BaseService
from src.services.errors import (
    InvalidRentalPeriodError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    RentalConfigNotFoundError,
    RentalUnavailableError,
)
from src.services.order.schemas import OrderStatus
from src.services.rental.interface import RentalServiceI
from src.services.rental.schemas import (
    ProductRentalCalendarResponse,
    ProductRentalCalendarSlot,
    RentalOrderDetail,
    RentalOrderItemBrief,
    RentalOrderSummary,
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    # Matches the admin bot's keyboard (bot/src/handlers/admin_callbacks.py
    # _order_keyboard): every active status offers Pause, Close and Returned
    # (except canceled, which is terminal), so those must all be reachable from
    # every non-terminal status. TAKEN ("Отдал" — handed over to the client) is
    # only reachable from IN_PROGRESS: you can't hand over gear before payment
    # is confirmed. RETURNED and COMPLETED are both terminal-ish success/failure
    # outcomes for revenue stats (see calendar_sync.py and _get_order_reservations
    # — neither blocks availability): RETURNED means the client gave the gear
    # back (successful order); COMPLETED means the order was closed WITHOUT a
    # successful return (no-show, dispute, etc. — no revenue). Availability is
    # only re-checked for transitions INTO in_progress/taken (see
    # update_rental_status) — pausing/closing/returning only releases a slot,
    # never claims one, so no re-check is needed there.
    #
    # TAKEN -> IN_PROGRESS and RETURNED -> TAKEN are admin mistake-correction
    # ("Отменить отдал" / "Отменить возврат") — undoing a handover/return re-enters
    # a slot-holding status, so it goes through the same availability re-check as
    # any other entry into IN_PROGRESS/TAKEN (harmless if nothing conflicts, but
    # correctly rejects if someone else booked the now-freed slot in the meantime).
    OrderStatus.CREATED.value: {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.PAUSED.value,
        OrderStatus.COMPLETED.value,
        OrderStatus.CANCELED.value,
    },
    OrderStatus.IN_PROGRESS.value: {
        OrderStatus.TAKEN.value,
        OrderStatus.PAUSED.value,
        OrderStatus.CANCELED.value,
        OrderStatus.COMPLETED.value,
        OrderStatus.RETURNED.value,
    },
    OrderStatus.TAKEN.value: {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.PAUSED.value,
        OrderStatus.COMPLETED.value,
        OrderStatus.CANCELED.value,
        OrderStatus.RETURNED.value,
    },
    OrderStatus.PAUSED.value: {
        OrderStatus.IN_PROGRESS.value,
        OrderStatus.COMPLETED.value,
        OrderStatus.CANCELED.value,
        OrderStatus.RETURNED.value,
    },
    OrderStatus.RETURNED.value: {OrderStatus.TAKEN.value},
    OrderStatus.COMPLETED.value: {OrderStatus.IN_PROGRESS.value},
    OrderStatus.CANCELED.value: set(),
}


@dataclass(slots=True)
class _ReservationInterval:
    start: datetime
    end: datetime
    quantity: int


@dataclass(slots=True)
class _WindowAvailability:
    slot_start: datetime
    slot_end: datetime
    effective_capacity: int
    manual_reserved_quantity: int
    blocked_quantity: int
    order_reserved_quantity: int
    is_closed: bool

    @property
    def available_quantity(self) -> int:
        if self.is_closed:
            return 0
        return max(
            0,
            self.effective_capacity
            - self.manual_reserved_quantity
            - self.blocked_quantity
            - self.order_reserved_quantity,
        )


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

            slot_size = slot_minutes or rental.slot_duration_minutes
            if slot_size <= 0:
                raise InvalidRentalPeriodError("slot_minutes must be positive")

            windows = await self._compute_windows(session, rental, date_from, date_to, slot_size)

            return ProductRentalCalendarResponse(
                product_id=product_id,
                rental_id=rental.rental_id,
                total_quantity=rental.total_quantity,
                slot_duration_minutes=rental.slot_duration_minutes,
                range_start=date_from,
                range_end=date_to,
                slots=[
                    ProductRentalCalendarSlot(
                        slot_start=window.slot_start,
                        slot_end=window.slot_end,
                        effective_capacity=window.effective_capacity,
                        order_reserved_quantity=window.order_reserved_quantity,
                        manual_reserved_quantity=window.manual_reserved_quantity,
                        blocked_quantity=window.blocked_quantity,
                        available_quantity=window.available_quantity,
                        is_closed=window.is_closed,
                        is_available=window.available_quantity > 0,
                    )
                    for window in windows
                ],
            )

    async def ensure_product_available(
        self,
        session: AsyncSession,
        product_id: int,
        quantity: int,
        rental_start: datetime | None,
        rental_end: datetime | None,
        exclude_order_id: int | None = None,
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

        windows = await self._compute_windows(
            session, rental, rental_start, rental_end, rental.slot_duration_minutes, exclude_order_id=exclude_order_id
        )
        for window in windows:
            if window.is_closed:
                raise RentalUnavailableError("Rental slot is closed")
            if window.available_quantity < quantity:
                raise RentalUnavailableError(
                    f"Not enough quantity for rental window {window.slot_start.isoformat()} - {window.slot_end.isoformat()}"
                )

    async def available_quantity_for_window(
        self,
        session: AsyncSession,
        product_id: int,
        rental_start: datetime,
        rental_end: datetime,
    ) -> int | None:
        """Max quantity of a product bookable across the whole window.

        Returns None when the product is not rentable (no availability cap
        applies). Otherwise the minimum available quantity over every slot in the
        window (0 if any slot is closed/full). Runs on the caller's session so it
        can share a transaction with a basket migration.
        """
        rental = await self._get_product_rental(session, product_id, for_update=True, allow_missing=True)
        if not rental or not rental.is_enabled:
            return None

        self._validate_period(rental_start, rental_end)
        windows = await self._compute_windows(session, rental, rental_start, rental_end, rental.slot_duration_minutes)
        if not windows:
            return 0
        return max(0, min(window.available_quantity for window in windows))

    def get_allowed_transitions(self, status: str) -> list[str]:
        return sorted(ALLOWED_TRANSITIONS.get(status, set()))

    async def list_admin_rentals(
        self,
        date_from: datetime,
        date_to: datetime,
        status: OrderStatus | None = None,
    ) -> list[RentalOrderSummary]:
        self._validate_period(date_from, date_to)

        async with self.session() as session:
            stmt = (
                select(Order)
                .join(OrderItem, OrderItem.order_id == Order.order_id)
                .where(
                    OrderItem.rental_start.is_not(None),
                    OrderItem.rental_end.is_not(None),
                    OrderItem.rental_start < date_to,
                    OrderItem.rental_end > date_from,
                )
                .options(selectinload(Order.items).selectinload(OrderItem.product))
                .distinct()
            )
            if status is not None:
                stmt = stmt.where(Order.status == status.value)

            result = await session.execute(stmt)
            orders = result.scalars().unique().all()

            users_by_id = await self._get_users_by_id(session, {order.user_id for order in orders})

            return [self._to_rental_summary(order, users_by_id.get(order.user_id)) for order in orders]

    async def get_admin_rental(self, order_id: int) -> RentalOrderDetail:
        async with self.session() as session:
            stmt = (
                select(Order)
                .where(Order.order_id == order_id)
                .options(selectinload(Order.items).selectinload(OrderItem.product))
            )
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()
            if not order or not self._rental_items(order):
                raise OrderNotFoundError

            users_by_id = await self._get_users_by_id(session, {order.user_id})
            summary = self._to_rental_summary(order, users_by_id.get(order.user_id))

            return RentalOrderDetail(
                **summary.model_dump(),
                order_date=order.order_date,
                payment_option=order.payment_option,
                address=order.address,
                comment=order.comment,
                allowed_transitions=self.get_allowed_transitions(order.status),
            )

    async def update_rental_status(self, order_id: int, new_status: OrderStatus) -> None:
        async with self.session() as session, session.begin():
            result = await session.execute(
                select(Order).where(Order.order_id == order_id).options(selectinload(Order.items))
            )
            order = result.unique().scalar_one_or_none()
            if not order:
                raise OrderNotFoundError

            allowed = ALLOWED_TRANSITIONS.get(order.status, set())
            if new_status.value not in allowed:
                raise InvalidStatusTransitionError(
                    f"Cannot transition order from '{order.status}' to '{new_status.value}'"
                )

            # Entering a slot-holding status (in_progress/taken) is the moment a
            # reservation becomes real/indefinite — re-check availability so a slot
            # claimed by someone else in the meantime can't be double-booked. This
            # covers every path in, not just the first confirmation: created (hold
            # expired or not), paused -> in_progress (resume), and completed ->
            # in_progress (reopen) all come from statuses that don't hold the slot,
            # so the slot may have been taken by someone else while this order sat
            # there. in_progress -> taken re-checks too — harmless (already held).
            entering_confirmed_status = new_status.value in {OrderStatus.IN_PROGRESS.value, OrderStatus.TAKEN.value}
            if entering_confirmed_status:
                demands: dict[tuple[int, datetime, datetime], int] = {}
                for item in order.items:
                    if item.rental_start is None:
                        await self.ensure_product_available(
                            session=session,
                            product_id=item.product_id,
                            quantity=item.quantity,
                            rental_start=None,
                            rental_end=None,
                        )
                        continue
                    key = (item.product_id, item.rental_start, item.rental_end)
                    demands[key] = demands.get(key, 0) + item.quantity

                for (product_id, rental_start, rental_end), quantity in demands.items():
                    await self.ensure_product_available(
                        session=session,
                        product_id=product_id,
                        quantity=quantity,
                        rental_start=rental_start,
                        rental_end=rental_end,
                        exclude_order_id=order.order_id,
                    )

            order.status = new_status.value

    async def _get_users_by_id(self, session: AsyncSession, user_ids: set[int]) -> dict[int, User]:
        if not user_ids:
            return {}
        result = await session.execute(select(User).where(User.user_id.in_(user_ids)))
        return {user.user_id: user for user in result.scalars().all()}

    @staticmethod
    def _rental_items(order: Order) -> list[OrderItem]:
        return [item for item in order.items if item.rental_start is not None and item.rental_end is not None]

    def _to_rental_summary(self, order: Order, user: User | None) -> RentalOrderSummary:
        rental_items = self._rental_items(order)
        return RentalOrderSummary(
            order_id=order.order_id,
            telegram_id=order.user_id,
            first_name=(user.first_name if user else None) or order.first_name,
            username=user.username if user else None,
            phone=(user.phone_number if user else None) or order.phone,
            status=OrderStatus(order.status),
            rental_start=min(item.rental_start for item in rental_items),
            rental_end=max(item.rental_end for item in rental_items),
            total_price=order.total_price,
            items=[
                RentalOrderItemBrief(
                    order_item_id=item.order_item_id,
                    product_id=item.product_id,
                    product_name=item.product.name if item.product else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    rental_start=item.rental_start,
                    rental_end=item.rental_end,
                )
                for item in order.items
            ],
        )

    async def _compute_windows(
        self,
        session: AsyncSession,
        rental: ProductRental,
        date_from: datetime,
        date_to: datetime,
        slot_minutes: int,
        exclude_order_id: int | None = None,
    ) -> list[_WindowAvailability]:
        """Single source of truth for slot availability, shared by the calendar view and the booking check.

        `exclude_order_id` leaves one order's own reservation out of the count —
        used when re-checking availability for that same order's own confirmation,
        so its own (already-counted) hold doesn't make the slot look full to itself.
        """
        manual_slots = await self._get_manual_slots(session, rental.rental_id, date_from, date_to)
        order_intervals = await self._get_order_reservations(
            session, rental.product_id, date_from, date_to, exclude_order_id=exclude_order_id
        )

        windows = []
        for slot_start, slot_end in self._iter_slots(date_from, date_to, slot_minutes):
            manual_state = self._manual_state_for_window(manual_slots, slot_start, slot_end, rental.total_quantity)
            windows.append(
                _WindowAvailability(
                    slot_start=slot_start,
                    slot_end=slot_end,
                    effective_capacity=manual_state["effective_capacity"],
                    manual_reserved_quantity=manual_state["manual_reserved_quantity"],
                    blocked_quantity=manual_state["blocked_quantity"],
                    order_reserved_quantity=self._peak_reserved_quantity(order_intervals, slot_start, slot_end),
                    is_closed=manual_state["is_closed"],
                )
            )
        return windows

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
        exclude_order_id: int | None = None,
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
                # A confirmed order (in_progress/taken) always blocks. A brand-new
                # "created" order blocks only until its payment hold expires — after
                # that it stops reserving (but isn't cancelled) unless a conflict
                # forces it, see tasks/payment_holds.py.
                or_(
                    Order.status.in_([OrderStatus.IN_PROGRESS.value, OrderStatus.TAKEN.value]),
                    and_(
                        Order.status == OrderStatus.CREATED.value,
                        Order.payment_deadline > func.now(),
                    ),
                ),
            )
        )
        if exclude_order_id is not None:
            stmt = stmt.where(Order.order_id != exclude_order_id)
        stmt = stmt.group_by(OrderItem.rental_start, OrderItem.rental_end)
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
