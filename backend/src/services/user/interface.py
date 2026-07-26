from abc import abstractmethod
from typing import Protocol

from src.services.user.schemas import UserCreate, UserResponse, UserUpdate


class UserServiceI(Protocol):
    @abstractmethod
    async def create(self, user: UserCreate) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: int) -> UserResponse:
        ...

    @abstractmethod
    async def update(self, user_id: int, data: UserUpdate) -> UserResponse:
        ...

    @abstractmethod
    async def get_by_phone(self, phone_number: str) -> UserResponse | None:
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> UserResponse | None:
        ...

    @abstractmethod
    async def create_by_phone(self, phone_number: str, first_name: str, last_name: str | None = None) -> UserResponse:
        ...

    @abstractmethod
    async def get_admins(self) -> list[int]:
        ...
