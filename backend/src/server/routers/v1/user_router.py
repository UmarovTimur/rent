from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import JSONResponse

from src.container import container
from src.server.dependencies import Caller, require_internal, require_user_or_internal
from src.services.static import create_message
from src.services.user.interface import UserServiceI
from src.services.user.schemas import UserCreate, UserResponse, UserUpdate

_SUPPORTED_LANGS = {"ru", "uz"}

user_tag = "Users"
router = APIRouter(prefix="/users", tags=[user_tag])


async def get_user_service() -> UserServiceI:
    return container.user_service()


@router.post("/create_user", dependencies=[Depends(require_internal)])
async def create_user(
    user: UserCreate,
    user_service: UserServiceI = Depends(get_user_service),
) -> JSONResponse:
    # Privilege/balance fields are never set from an incoming payload — admins are
    # managed in the admin panel, coins server-side.
    user.is_admin = None
    user.coins = None
    await user_service.create(user)
    return JSONResponse(content={"message": create_message.format(entity=user_tag)}, status_code=HTTPStatus.CREATED)


@router.patch("/update_user", response_model=UserResponse, dependencies=[Depends(require_internal)])
async def update_user(
    user_id: int,
    data: UserUpdate,
    user_service: UserServiceI = Depends(get_user_service),
) -> UserResponse:
    return await user_service.update(user_id, data)


@router.patch("/me/language", response_model=UserResponse)
async def set_my_language(
    language: str,
    caller: Caller = Depends(require_user_or_internal),
    user_service: UserServiceI = Depends(get_user_service),
) -> UserResponse:
    # A Mini App user may only change their own language; the language set is
    # restricted to what the UI supports.
    if caller.user_id is None:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="user_id required")
    if language not in _SUPPORTED_LANGS:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Unsupported language")
    return await user_service.update(caller.user_id, UserUpdate(language_code=language))


@router.get("/get_user_by_id", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    caller: Caller = Depends(require_user_or_internal),
    user_service: UserServiceI = Depends(get_user_service),
) -> UserResponse:
    caller.authorize_user(user_id)
    return await user_service.get_by_id(user_id)


@router.get("/get_by_username", response_model=UserResponse, dependencies=[Depends(require_internal)])
async def get_by_username(
    username: str,
    user_service: UserServiceI = Depends(get_user_service),
) -> UserResponse:
    # Internal-only (bot admin flows): resolve @username → user reliably from our
    # own DB, since the Telegram Bot API can't look up arbitrary usernames.
    user = await user_service.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="User not found")
    return user


@router.get("/admins", response_model=list[int], dependencies=[Depends(require_internal)])
async def get_admins(
    user_service: UserServiceI = Depends(get_user_service),
) -> list[int]:
    return await user_service.get_admins()
