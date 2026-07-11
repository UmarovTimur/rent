from http import HTTPStatus

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from src.container import container
from src.server.dependencies import Caller, require_internal, require_user_or_internal
from src.services.static import create_message
from src.services.user.interface import UserServiceI
from src.services.user.schemas import UserCreate, UserResponse, UserUpdate

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


@router.get("/get_user_by_id", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    caller: Caller = Depends(require_user_or_internal),
    user_service: UserServiceI = Depends(get_user_service),
) -> UserResponse:
    caller.authorize_user(user_id)
    return await user_service.get_by_id(user_id)


@router.get("/admins", response_model=list[int], dependencies=[Depends(require_internal)])
async def get_admins(
    user_service: UserServiceI = Depends(get_user_service),
) -> list[int]:
    return await user_service.get_admins()
