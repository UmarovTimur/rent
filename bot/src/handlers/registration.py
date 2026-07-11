"""Registration flow: collect phone (via contact button) and name on first /start.

The collected data lands on the backend User record and is auto-filled into
the Mini App order form (frontend OrderContext prefills first_name/phone_number).
"""

import asyncio
import logging
import re
from http import HTTPStatus

import aiohttp
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from src.config import INTERNAL_HEADERS, REQUEST_TIMEOUT, update_user_url

router = Router(name="registration")
logger = logging.getLogger(__name__)

SERVICE_UNAVAILABLE_TEXT = "Сервис временно недоступен. Пожалуйста, попробуйте позже."
PHONE_PROMPT_TEXT = (
    "Чтобы оформлять заказы, нам нужен ваш номер телефона.\n"
    "Нажмите кнопку ниже, чтобы поделиться контактом 👇\n\n"
    "Или просто отправьте номер сообщением, например: +998 90 123 45 67"
)
PHONE_INVALID_TEXT = (
    "Не похоже на номер телефона 🤔\n"
    "Нажмите кнопку «📱 Отправить номер» или пришлите номер в формате +998 90 123 45 67."
)
FOREIGN_CONTACT_TEXT = "Пожалуйста, отправьте свой собственный контакт кнопкой ниже."
NAME_PROMPT_TEXT = "Отлично! Как к вам обращаться? Напишите имя или выберите вариант ниже 👇"
NAME_INVALID_TEXT = "Пожалуйста, отправьте имя обычным текстовым сообщением."
DONE_TEXT = (
    "✅ Регистрация завершена!\n\n"
    "Нажмите на кнопку «Магазин», чтобы открыть мини-приложение — "
    "имя и телефон подставятся в заказ автоматически."
)

_PHONE_RE = re.compile(r"^\+?\d{9,15}$")


class Registration(StatesGroup):
    waiting_phone = State()
    waiting_name = State()


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _name_suggestion_keyboard(suggestion: str | None) -> ReplyKeyboardMarkup | ReplyKeyboardRemove:
    if not suggestion:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=suggestion)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[\s\-()]+", "", raw)
    if not _PHONE_RE.fullmatch(digits):
        return None
    return digits if digits.startswith("+") else f"+{digits}"


async def _patch_user(user_id: int, payload: dict) -> bool:
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.patch(
                update_user_url, params={"user_id": user_id}, json=payload, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    return True
                body = await resp.text()
                logger.warning(
                    "update_user failed: status=%s user_id=%s body=%s",
                    resp.status,
                    user_id,
                    body[:300],
                )
                return False
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("update_user request failed for user_id=%s", user_id)
        return False


async def start_registration(message: Message, state: FSMContext) -> None:
    """Entry point, called from /start when the user has no phone on record."""
    await state.set_state(Registration.waiting_phone)
    await message.answer(PHONE_PROMPT_TEXT, reply_markup=phone_request_keyboard())


async def _save_phone_and_ask_name(
    message: Message, state: FSMContext, phone: str
) -> None:
    if not message.from_user:
        return

    if not await _patch_user(message.from_user.id, {"phone_number": phone}):
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return

    await state.set_state(Registration.waiting_name)
    await message.answer(
        NAME_PROMPT_TEXT,
        reply_markup=_name_suggestion_keyboard(message.from_user.first_name),
    )


@router.message(Registration.waiting_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.contact:
        return

    # Only the user's own contact counts as their phone number.
    if message.contact.user_id != message.from_user.id:
        await message.answer(FOREIGN_CONTACT_TEXT, reply_markup=phone_request_keyboard())
        return

    phone = normalize_phone(message.contact.phone_number or "")
    if not phone:
        await message.answer(PHONE_INVALID_TEXT, reply_markup=phone_request_keyboard())
        return

    await _save_phone_and_ask_name(message, state, phone)


# Commands ("/start" etc.) are excluded at the filter level so they fall
# through to their own handlers in message_router (a matched handler would
# otherwise stop propagation).
@router.message(Registration.waiting_phone, F.text, ~F.text.startswith("/"))
async def handle_phone_text(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text or "")
    if not phone:
        await message.answer(PHONE_INVALID_TEXT, reply_markup=phone_request_keyboard())
        return

    await _save_phone_and_ask_name(message, state, phone)


@router.message(Registration.waiting_phone, ~F.text)
async def handle_phone_other(message: Message) -> None:
    # Contact messages are caught by handle_contact above (registration order).
    await message.answer(PHONE_INVALID_TEXT, reply_markup=phone_request_keyboard())


@router.message(Registration.waiting_name, F.text, ~F.text.startswith("/"))
async def handle_name(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer(NAME_INVALID_TEXT)
        return

    if not await _patch_user(message.from_user.id, {"first_name": name}):
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return

    await state.clear()
    await message.answer(DONE_TEXT, reply_markup=ReplyKeyboardRemove())


@router.message(Registration.waiting_name, ~F.text)
async def handle_name_other(message: Message) -> None:
    await message.answer(NAME_INVALID_TEXT)
