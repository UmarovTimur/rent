from pydantic import BaseModel


class UserCreate(BaseModel):
    user_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    coins: float | None = None
    phone_number: str | None = None
    is_admin: bool | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Partial update — only provided (non-None) fields are written."""

    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class UserResponse(BaseModel):
    user_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    language_code: str | None
    coins: float | None
    phone_number: str | None = None
    is_admin: bool | None = None

    class Config:
        from_attributes = True
