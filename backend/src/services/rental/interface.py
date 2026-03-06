from abc import abstractmethod
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.rental.schemas import ProductRentalCalendarResponse


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
