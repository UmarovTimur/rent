from abc import abstractmethod
from typing import Protocol

from src.services.category.schemas import CategoryCreate, CategoryResponse, CategoryUpdate


class CategoryServiceI(Protocol):
    @abstractmethod
    async def create(self, category: CategoryCreate) -> CategoryResponse:
        ...

    @abstractmethod
    async def get_all(self) -> list[CategoryResponse]:
        ...

    @abstractmethod
    async def update(self, category_id: int, category_data: CategoryUpdate) -> None:
        ...

    @abstractmethod
    async def delete(self, category_id: int) -> None:
        ...
