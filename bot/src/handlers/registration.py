"""Registration flow: pick language, then collect phone (via contact button)
and name on first /start.

The collected data lands on the backend User record and is auto-filled into
the Mini App order form (frontend OrderContext prefills first_name/phone_number).
The chosen language (User.language_code) drives all client-facing bot text and
the Mini App interface language.
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
    CallbackQuery,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import INTERNAL_HEADERS, REQUEST_TIMEOUT, update_user_url
from src.i18n import normalize_lang, t

router = Router(name="registration")
logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"^\+?\d{9,15}$")


class Registration(StatesGroup):
    waiting_language = State()
    waiting_phone = State()
    waiting_name = State()


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="setlang:ru")
    builder.button(text="🇺🇿 O‘zbekcha", callback_data="setlang:uz")
    builder.adjust(2)
    return builder.as_markup()


def phone_request_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("phone_button", lang), request_contact=True)]],
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


async def _lang(state: FSMContext) -> str:
    data = await state.get_data()
    return normalize_lang(data.get("lang"))


async def start_registration(message: Message, state: FSMContext) -> None:
    """Entry point, called from /start when the user has no phone on record.

    Begins by asking for a language (bilingual prompt) — everything after is
    shown in the chosen language.
    """
    await state.set_state(Registration.waiting_language)
    await message.answer(t("choose_language", None), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("setlang:"))
async def handle_language_choice(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not callback.data:
        return
    lang = normalize_lang(callback.data.split(":")[1])
    await callback.answer()

    await _patch_user(callback.from_user.id, {"language_code": lang})
    await state.update_data(lang=lang)

    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(t("language_set", lang))

    # Standalone /language change (user already registered) leaves no pending
    # registration state — only continue the flow when we're mid-registration.
    current = await state.get_state()
    if current == Registration.waiting_language.state and isinstance(callback.message, Message):
        await state.set_state(Registration.waiting_phone)
        await callback.message.answer(t("phone_prompt", lang), reply_markup=phone_request_keyboard(lang))


async def _save_phone_and_ask_name(message: Message, state: FSMContext, phone: str) -> None:
    if not message.from_user:
        return
    lang = await _lang(state)

    if not await _patch_user(message.from_user.id, {"phone_number": phone}):
        await message.answer(t("service_unavailable", lang))
        return

    await state.set_state(Registration.waiting_name)
    await message.answer(
        t("name_prompt", lang),
        reply_markup=_name_suggestion_keyboard(message.from_user.first_name),
    )


@router.message(Registration.waiting_language, ~F.text.startswith("/"))
async def handle_language_text(message: Message) -> None:
    # The user typed instead of tapping a language button — re-prompt.
    await message.answer(t("choose_language", None), reply_markup=language_keyboard())


@router.message(Registration.waiting_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext) -> None:
    if not message.from_user or not message.contact:
        return
    lang = await _lang(state)

    # Only the user's own contact counts as their phone number.
    if message.contact.user_id != message.from_user.id:
        await message.answer(t("foreign_contact", lang), reply_markup=phone_request_keyboard(lang))
        return

    phone = normalize_phone(message.contact.phone_number or "")
    if not phone:
        await message.answer(t("phone_invalid", lang), reply_markup=phone_request_keyboard(lang))
        return

    await _save_phone_and_ask_name(message, state, phone)


# Commands ("/start" etc.) are excluded at the filter level so they fall
# through to their own handlers in message_router (a matched handler would
# otherwise stop propagation).
@router.message(Registration.waiting_phone, F.text, ~F.text.startswith("/"))
async def handle_phone_text(message: Message, state: FSMContext) -> None:
    lang = await _lang(state)
    phone = normalize_phone(message.text or "")
    if not phone:
        await message.answer(t("phone_invalid", lang), reply_markup=phone_request_keyboard(lang))
        return

    await _save_phone_and_ask_name(message, state, phone)


@router.message(Registration.waiting_phone, ~F.text)
async def handle_phone_other(message: Message, state: FSMContext) -> None:
    lang = await _lang(state)
    # Contact messages are caught by handle_contact above (registration order).
    await message.answer(t("phone_invalid", lang), reply_markup=phone_request_keyboard(lang))


@router.message(Registration.waiting_name, F.text, ~F.text.startswith("/"))
async def handle_name(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    lang = await _lang(state)

    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer(t("name_invalid", lang))
        return

    if not await _patch_user(message.from_user.id, {"first_name": name}):
        await message.answer(t("service_unavailable", lang))
        return

    await state.clear()
    await message.answer(t("registration_done", lang), reply_markup=ReplyKeyboardRemove())


@router.message(Registration.waiting_name, ~F.text)
async def handle_name_other(message: Message, state: FSMContext) -> None:
    lang = await _lang(state)
    await message.answer(t("name_invalid", lang))
