from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from starlette.requests import Request

from src.admin.auth import SESSION_ADMIN_ID, SESSION_ADMIN_USERNAME
from src.container import container
from src.services.admin_auth import authenticate_admin

router = APIRouter(prefix="/admin", tags=["Admin Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminInfo(BaseModel):
    username: str


@router.post("/login", response_model=AdminInfo)
async def login(payload: LoginRequest, request: Request) -> AdminInfo:
    async with container.database().get_session() as session:
        admin = await authenticate_admin(session, payload.username.strip(), payload.password)

    if admin is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid username or password")

    request.session[SESSION_ADMIN_ID] = admin.id
    request.session[SESSION_ADMIN_USERNAME] = admin.username
    return AdminInfo(username=admin.username)


@router.post("/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get("/me", response_model=AdminInfo)
async def me(request: Request) -> AdminInfo:
    if not request.session.get(SESSION_ADMIN_ID):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Not authenticated")
    return AdminInfo(username=request.session.get(SESSION_ADMIN_USERNAME, ""))
