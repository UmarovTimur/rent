from abc import abstractmethod
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.order.schemas import OrderStatus
from src.services.rental.schemas import (
    ProductRentalCalendarResponse,
    RentalOrderDetail,
    RentalOrderSummary,
)


class RentalServiceI(Protocol):
    @abstractmethod
    async def get_product_calendar(
        self,
        product_id: int,
        date_from: datetime,
        date_to: datetime,
        slot_minutes: int | None = None,
    ) -> ProductRentalCalendarResponse: ...

    @abstractmethod
    async def ensure_product_available(
        self,
        session: AsyncSession,
        product_id: int,
        quantity: int,
        rental_start: datetime | None,
        rental_end: datetime | None,
    ) -> None: ...

    @abstractmethod
    async def available_quantity_for_window(
        self,
        session: AsyncSession,
        product_id: int,
        rental_start: datetime,
        rental_end: datetime,
    ) -> int | None: ...

    @abstractmethod
    def get_allowed_transitions(self, status: str) -> list[str]: ...

    @abstractmethod
    async def list_admin_rentals(
        self,
        date_from: datetime,
        date_to: datetime,
        status: OrderStatus | None = None,
    ) -> list[RentalOrderSummary]: ...

    @abstractmethod
    async def get_admin_rental(self, order_id: int) -> RentalOrderDetail: ...

    @abstractmethod
    async def update_rental_status(self, order_id: int, new_status: OrderStatus) -> None: ...
