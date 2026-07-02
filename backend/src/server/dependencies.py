from http import HTTPStatus

from fastapi import Depends, Header, HTTPException

from src.container import container
from src.services.telegram_auth import validate_init_data
from src.settings.admin import AdminSettings
from src.settings.telegram import TelegramSettings


async def get_telegram_settings() -> TelegramSettings:
    return container.telegram_settings()


async def get_admin_settings() -> AdminSettings:
    return container.admin_settings()


async def require_admin(
    x_telegram_init_data: str | None = Header(None, alias="X-Telegram-Init-Data"),
    telegram_settings: TelegramSettings = Depends(get_telegram_settings),
    admin_settings: AdminSettings = Depends(get_admin_settings),
) -> int:
    if not x_telegram_init_data:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Missing X-Telegram-Init-Data header")

    try:
        data = validate_init_data(x_telegram_init_data, telegram_settings.token)
        user = data.get("user")
        if not isinstance(user, dict) or "id" not in user:
            raise ValueError("initData is missing user id")
        telegram_id = int(user["id"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Invalid Telegram initData") from exc

    if telegram_id not in admin_settings.telegram_ids:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not an admin")

    return telegram_id
