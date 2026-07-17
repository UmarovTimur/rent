from abc import abstractmethod
from typing import Protocol

from src.services.promo.schemas import PromoResponse


class PromoServiceI(Protocol):
    @abstractmethod
    async def list_active(self) -> list[PromoResponse]: ...
