from dataclasses import dataclass
from http import HTTPStatus

from fastapi import Depends, Header, HTTPException
from starlette.requests import Request

from src.admin.auth import SESSION_ADMIN_ID
from src.container import container
from src.services.admin_auth import admin_exists
from src.services.telegram_auth import validate_init_data
from src.settings.internal import InternalSettings
from src.settings.telegram import TelegramSettings


async def get_telegram_settings() -> TelegramSettings:
    return container.telegram_settings()


async def get_internal_settings() -> InternalSettings:
    return container.internal_settings()


async def require_admin(request: Request) -> int:
    """Authorise a request using the shared admin session cookie.

    The same cookie is set by the SQLAdmin login form and by the calendar's JSON
    login endpoint, so a single login unlocks both the panel and the calendar.
    """
    admin_id = request.session.get(SESSION_ADMIN_ID)
    if not admin_id:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Not authenticated")

    async with container.database().get_session() as session:
        if not await admin_exists(session, int(admin_id)):
            request.session.clear()
            raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Not authenticated")

    return int(admin_id)


def _telegram_user_id(init_data: str | None, token: str) -> int | None:
    if not init_data:
        return None
    try:
        data = validate_init_data(init_data, token)
        user = data.get("user")
        if not isinstance(user, dict) or "id" not in user:
            return None
        return int(user["id"])
    except (ValueError, TypeError):
        return None


async def require_telegram_user(
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    telegram_settings: TelegramSettings = Depends(get_telegram_settings),
) -> int:
    """Authenticate a Mini App request from its Telegram initData.

    Returns the verified Telegram user id — the trusted identity for the request.
    Never trust a user_id taken from the path/query/body; use this instead.
    """
    user_id = _telegram_user_id(x_telegram_init_data, telegram_settings.token)
    if user_id is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid or missing Telegram initData")
    return user_id


def _is_internal(token: str | None, expected: str) -> bool:
    return bool(expected) and token == expected


async def require_internal(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
    internal_settings: InternalSettings = Depends(get_internal_settings),
) -> None:
    """Authorise a trusted server-to-server call (the bot) via a shared secret."""
    if not _is_internal(x_internal_token, internal_settings.api_token):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid internal token")


@dataclass
class Caller:
    """Who is making the request: a specific Telegram user, or a trusted service."""

    user_id: int | None
    is_internal: bool

    def authorize_user(self, target_user_id: int) -> None:
        """Allow if the caller is the target user, or a trusted service."""
        if self.is_internal:
            return
        if self.user_id is not None and self.user_id == target_user_id:
            return
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not allowed")


async def require_user_or_internal(
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
    telegram_settings: TelegramSettings = Depends(get_telegram_settings),
    internal_settings: InternalSettings = Depends(get_internal_settings),
) -> Caller:
    """Accept either a Telegram user (Mini App) or the trusted service (bot)."""
    if _is_internal(x_internal_token, internal_settings.api_token):
        return Caller(user_id=None, is_internal=True)

    user_id = _telegram_user_id(x_telegram_init_data, telegram_settings.token)
    if user_id is not None:
        return Caller(user_id=user_id, is_internal=False)

    raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Not authenticated")
