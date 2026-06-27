import random

from pydantic import TypeAdapter
from sqlalchemy import select

from src.clients.database.models.user import User
from src.services.base import BaseService
from src.services.errors import UserNotFoundError
from src.services.user.interface import UserServiceI
from src.services.user.schemas import UserCreate, UserResponse


class UserService(BaseService, UserServiceI):
    async def create(self, user: UserCreate) -> None:
        async with self.session() as session, session.begin():
            new_user = User(**user.model_dump())
            session.add(new_user)

    async def get_by_id(self, user_id: int) -> UserResponse:
        async with self.session() as session, session.begin():
            query = select(User).where(User.user_id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            if not user:
                raise UserNotFoundError

        type_adapter = TypeAdapter(UserResponse)
        return type_adapter.validate_python(user)

    async def get_by_phone(self, phone_number: str) -> UserResponse | None:
        async with self.session() as session, session.begin():
            result = await session.execute(select(User).where(User.phone_number == phone_number))
            user = result.scalar_one_or_none()
            if not user:
                return None
        type_adapter = TypeAdapter(UserResponse)
        return type_adapter.validate_python(user)

    async def create_by_phone(self, phone_number: str, first_name: str, last_name: str | None = None) -> UserResponse:
        async with self.session() as session, session.begin():
            # Negative IDs for phone-registered web users — Telegram IDs are always positive
            while True:
                new_id = -random.randint(1, 2_000_000_000)
                if not await session.get(User, new_id):
                    break
            user = User(user_id=new_id, phone_number=phone_number, first_name=first_name, last_name=last_name)
            session.add(user)

        type_adapter = TypeAdapter(UserResponse)
        return type_adapter.validate_python(user)

    async def get_admins(self) -> list[int]:
        async with self.session() as session, session.begin():
            query = select(User.user_id).where(User.is_admin == True)  # noqa: E712
            result = await session.execute(query)
            return list(result.scalars().all())
