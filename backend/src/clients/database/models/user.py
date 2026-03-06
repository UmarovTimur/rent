from sqlalchemy.orm import Mapped, mapped_column

from src.clients.database.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    first_name: Mapped[str] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column(nullable=True)
    language_code: Mapped[str] = mapped_column(nullable=True)
    coins: Mapped[float] = mapped_column(nullable=True)
    is_admin: Mapped[bool] = mapped_column(nullable=True)

    def __str__(self) -> str:
        if self.username:
            return f"@{self.username}"
        full_name = " ".join(part for part in [self.first_name, self.last_name] if part)
        if full_name:
            return full_name
        return f"User #{self.user_id}"

    __repr__ = __str__
