import asyncio
import logging
from http import HTTPStatus

import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.config import create_user_url, get_user_by_id_url

router = Router(name="message_handlers")
logger = logging.getLogger(__name__)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)
SERVICE_UNAVAILABLE_TEXT = "Сервис временно недоступен. Пожалуйста, попробуйте позже."
UNEXPECTED_ERROR_TEXT = "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
WELCOME_TEXT = "Добро пожаловать! Нажмите на кнопку «Магазин», чтобы открыть мини-приложение."


@router.message(Command("start"))
async def send_welcome(message: Message) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            user_exists = False
            async with session.get(get_user_by_id_url, params={"user_id": user_id}) as resp:
                if resp.status == HTTPStatus.OK:
                    user_exists = True
                elif resp.status in {HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST}:
                    response_text = await resp.text()
                    # Backend returns 400 for "user not found" via global exception mapping.
                    if (
                        resp.status == HTTPStatus.NOT_FOUND
                        or "user not found" in response_text.lower()
                    ):
                        user_exists = False
                    else:
                        logger.warning(
                            "Unexpected get_user_by_id response: status=%s url=%s body=%s",
                            resp.status,
                            str(resp.url),
                            response_text[:300],
                        )
                        await message.answer(SERVICE_UNAVAILABLE_TEXT)
                        return
                else:
                    response_text = await resp.text()
                    logger.warning(
                        "Unexpected get_user_by_id response: status=%s url=%s body=%s",
                        resp.status,
                        str(resp.url),
                        response_text[:300],
                    )
                    await message.answer(SERVICE_UNAVAILABLE_TEXT)
                    return

            if not user_exists:
                user_data = {
                    "user_id": user_id,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "username": message.from_user.username,
                    "language_code": message.from_user.language_code,
                    "coins": 0,
                }
                async with session.post(create_user_url, json=user_data) as response:
                    if response.status not in {HTTPStatus.CREATED, HTTPStatus.OK}:
                        response_text = await response.text()
                        # In race conditions user can be created in parallel by another request.
                        if (
                            response.status == HTTPStatus.BAD_REQUEST
                            and "already exists" in response_text.lower()
                        ):
                            logger.info(
                                "User already exists during create_user race: user_id=%s",
                                user_id,
                            )
                        else:
                            logger.warning(
                                "Unexpected create_user response: status=%s url=%s body=%s",
                                response.status,
                                str(response.url),
                                response_text[:300],
                            )
                            await message.answer(SERVICE_UNAVAILABLE_TEXT)
                            return
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception(
            "Backend request failed for user_id=%s, get_url=%s, create_url=%s",
            user_id,
            get_user_by_id_url,
            create_user_url,
        )
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    except Exception:
        logger.exception("Unexpected error in /start handler for user_id=%s", user_id)
        await message.answer(UNEXPECTED_ERROR_TEXT)
        return

    await message.answer(WELCOME_TEXT)
