from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.container import container
from src.services.jwt_service import create_token
from src.services.user.interface import UserServiceI

router = APIRouter(prefix="/auth", tags=["Auth"])


async def get_user_service() -> UserServiceI:
    return container.user_service()


class PhoneCheckRequest(BaseModel):
    phone_number: str


class PhoneCheckResponse(BaseModel):
    exists: bool
    first_name: str | None = None


class PhoneLoginRequest(BaseModel):
    phone_number: str


class PhoneRegisterRequest(BaseModel):
    phone_number: str
    first_name: str
    last_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    user_id: int


@router.post("/phone/check", response_model=PhoneCheckResponse)
async def phone_check(
    data: PhoneCheckRequest,
    user_service: UserServiceI = Depends(get_user_service),
) -> PhoneCheckResponse:
    user = await user_service.get_by_phone(data.phone_number)
    if user:
        return PhoneCheckResponse(exists=True, first_name=user.first_name)
    return PhoneCheckResponse(exists=False)


@router.post("/phone/login", response_model=TokenResponse)
async def phone_login(
    data: PhoneLoginRequest,
    user_service: UserServiceI = Depends(get_user_service),
) -> TokenResponse:
    user = await user_service.get_by_phone(data.phone_number)
    if not user:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="User not found")
    return TokenResponse(access_token=create_token(user.user_id), user_id=user.user_id)


@router.post("/phone/register", response_model=TokenResponse, status_code=HTTPStatus.CREATED)
async def phone_register(
    data: PhoneRegisterRequest,
    user_service: UserServiceI = Depends(get_user_service),
) -> TokenResponse:
    existing = await user_service.get_by_phone(data.phone_number)
    if existing:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail="Phone already registered")
    user = await user_service.create_by_phone(data.phone_number, data.first_name, data.last_name)
    return TokenResponse(access_token=create_token(user.user_id), user_id=user.user_id)
