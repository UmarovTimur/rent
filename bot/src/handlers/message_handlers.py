import asyncio
import html
import logging
from http import HTTPStatus

import aiohttp
from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import (
    INTERNAL_HEADERS,
    MANAGER_USERNAME,
    PICKUP_ADDRESS,
    PICKUP_LATITUDE,
    PICKUP_LONGITUDE,
    REQUEST_TIMEOUT,
    admin_calendar_url,
    bot,
    change_status_url,
    create_user_url,
    fmt_price,
    get_all_orders_url,
    get_order_url,
    get_user_by_id_url,
)

from src.i18n import normalize_lang, status_label, t
from src.menu import CANCEL_LABEL, MENU_SEND, build_main_menu
from src.order_items import format_order_items
from src.user_lang import fetch_user_language

router = Router(name="message_handlers")
logger = logging.getLogger(__name__)
# Pre-language fallbacks: used only in error paths before we know the user's
# chosen language (defaults to Russian).
SERVICE_UNAVAILABLE_TEXT = t("service_unavailable", None)
UNEXPECTED_ERROR_TEXT = t("unexpected_error", None)


@router.message(Command("start"))
async def send_welcome(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id
    has_phone = False

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            user_exists = False
            async with session.get(
                get_user_by_id_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    user_exists = True
                    user_payload = await resp.json()
                    has_phone = bool(user_payload.get("phone_number"))
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
                async with session.post(create_user_url, json=user_data, headers=INTERNAL_HEADERS) as response:
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

    if not has_phone:
        # New user, or an old one without a phone on record — collect contact
        # details so the Mini App order form can be prefilled.
        from src.handlers.registration import start_registration

        await start_registration(message, state)
        return

    await state.clear()
    user_lang = normalize_lang(user_payload.get("language_code"))

    if user_payload.get("is_banned"):
        await message.answer(t("banned_notice", user_lang, manager=MANAGER_USERNAME))
        return

    await message.answer(
        t("welcome", user_lang),
        reply_markup=build_main_menu(
            is_admin=bool(user_payload.get("is_admin")),
            lang=user_lang,
            admin_calendar_url=admin_calendar_url,
        ),
    )


async def _send_language_picker(message: Message) -> None:
    from src.handlers.registration import language_keyboard

    await message.answer(t("choose_language", None), reply_markup=language_keyboard())


@router.message(Command("language"))
async def change_language(message: Message) -> None:
    await _send_language_picker(message)


@router.message(F.text.in_({t("menu_language", "ru"), t("menu_language", "uz")}), StateFilter(None))
async def menu_language_button(message: Message) -> None:
    await _send_language_picker(message)


# Orders the client would consider "still active" — created (awaiting payment
# confirmation), in_progress (paid/confirmed), paused, taken (gear handed
# over). Excludes finished outcomes (returned/completed) and canceled — this
# view is read-only status tracking, not a history log.
_ACTIVE_CLIENT_STATUSES = {"created", "in_progress", "paused", "taken"}


def _format_client_order(order: dict, lang: str) -> str:
    # No admin action buttons here on purpose — this is a read-only status
    # view for the client, management stays in the admin bot/panel.
    lines = [f"<b>#{order['order_id']}</b> — {status_label(order.get('status', ''), lang)}"]

    items = order.get("items", [])
    rental_starts = [i["rental_start"] for i in items if i.get("rental_start")]
    rental_ends = [i["rental_end"] for i in items if i.get("rental_end")]
    if rental_starts and rental_ends:
        start = min(rental_starts)[:16].replace("T", " ")
        end = max(rental_ends)[:16].replace("T", " ")
        lines.append(f"📆 {start} — {end}")

    items_text = format_order_items(items)
    if items_text:
        lines.append(t("order_items_header", lang, items=items_text).rstrip())

    payment_key = "pay_card" if order.get("payment_option") == "card" else "pay_cash"
    lines.append(f"💳 {t(payment_key, lang)}")
    lines.append(f"💰 {fmt_price(order['total_price'])} сум")
    lines.append(f"📍 {PICKUP_ADDRESS}")
    return "\n".join(lines)


@router.message(F.text.in_({t("menu_my_orders", "ru"), t("menu_my_orders", "uz")}), StateFilter(None))
async def menu_my_orders(message: Message) -> None:
    if not message.from_user:
        return
    user_id = message.from_user.id
    lang = await fetch_user_language(user_id)

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                get_all_orders_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.BAD_REQUEST:
                    orders = []
                elif resp.status != HTTPStatus.OK:
                    await message.answer(t("service_unavailable", lang))
                    return
                else:
                    orders = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Failed to fetch orders for user %s", user_id)
        await message.answer(t("service_unavailable", lang))
        return

    active_orders = [o for o in orders if o.get("status") in _ACTIVE_CLIENT_STATUSES]
    if not active_orders:
        await message.answer(t("my_orders_empty", lang))
        return

    active_orders.sort(key=lambda o: o["order_id"], reverse=True)
    text = t("my_orders_header", lang) + "\n\n" + "\n\n".join(
        _format_client_order(o, lang) for o in active_orders
    )
    await message.answer(text)


async def _process_receipt(
    bot: Bot,
    *,
    reply_chat_id: int,
    from_user_id: int,
    from_first_name: str | None,
    from_username: str | None,
    file_id: str,
    is_document: bool,
    order: dict,
) -> None:
    """Forward a receipt (photo or arbitrary file — screenshots and PDFs alike)
    to admins and auto-confirm the given order's payment right away — no admin
    click needed. This makes the hold permanent (see
    RentalService.update_rental_status, which re-checks availability on this
    exact transition). If someone else has since taken the slot, the
    confirmation is rejected (409): cancel this order and tell the client
    directly instead of leaving it stuck.
    """
    order_id = order["order_id"]
    # parse_mode=HTML is global — escape every client-controlled string so a
    # crafted name/comment can't break the caption (and silently drop it).
    client_label = f"@{html.escape(from_username)}" if from_username else f"ID: {from_user_id}"

    items = order.get("items", [])
    items_text = format_order_items(items)

    caption = (
        f"📎 <b>Чек об оплате депозита</b>\n"
        f"Клиент: {html.escape(from_first_name) if from_first_name else '—'} ({client_label})\n"
    )
    if order.get("phone"):
        caption += f"📞 {html.escape(str(order['phone']))}\n"
    caption += f"Заказ <b>#{order_id}</b> | {fmt_price(order['total_price'])} сум\n"
    if items_text:
        caption += f"\n<b>Состав:</b>\n{items_text}"

    from src.handlers.admin_callbacks import _order_keyboard, _register_order_card, get_admin_recipients

    lang = await fetch_user_language(from_user_id)
    await bot.send_message(reply_chat_id, t("receipt_received", lang))

    # Auto-confirm the payment FIRST (no admin click needed — the receipt IS the
    # confirmation). Only then forward the receipt to admins, so the card already
    # shows the real management buttons for the confirmed order instead of a
    # stale "Одобрить заказ" (which the earlier flow left and which now just
    # errors "already approved").
    confirmed = False
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.patch(
                f"{change_status_url}/{order_id}",
                params={"status": "in_progress"},
                headers=INTERNAL_HEADERS,
            ) as resp:
                confirmed = resp.status in {HTTPStatus.NO_CONTENT, HTTPStatus.OK}
            if not confirmed:
                # Slot taken in the meantime (409) — cancel so it isn't stuck.
                async with session.patch(
                    f"{change_status_url}/{order_id}",
                    params={"status": "canceled"},
                    headers=INTERNAL_HEADERS,
                ):
                    pass
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Failed to auto-confirm payment for order %s", order_id)

    # Forward the receipt to every admin with the buttons that match the order's
    # real post-confirmation status (in_progress → Отдал/Пауза/Закрыть;
    # canceled → no actions).
    final_status = "in_progress" if confirmed else "canceled"
    admin_caption = caption if confirmed else caption + "\n❌ Оплата не прошла — даты заняты, заказ отменён."
    kb = _order_keyboard(order_id, final_status)
    # A canceled order has no actions — _order_keyboard returns an empty markup,
    # which Telegram rejects; send without a keyboard in that case.
    keyboard = kb if kb.inline_keyboard else None
    for admin_id in await get_admin_recipients():
        try:
            # Documents (sent "as file") keep their original quality/format —
            # important for PDFs and for images some phones send uncompressed.
            # send_photo would reject a PDF outright and re-compress an image.
            if is_document:
                sent = await bot.send_document(admin_id, file_id, caption=admin_caption, reply_markup=keyboard)
            else:
                sent = await bot.send_photo(admin_id, file_id, caption=admin_caption, reply_markup=keyboard)
            _register_order_card(order_id, admin_id, sent.message_id)
        except Exception:
            logger.exception("Failed to forward receipt to admin %s", admin_id)

    if confirmed:
        await bot.send_message(reply_chat_id, t("payment_confirmed", lang, order_id=order_id))
        try:
            await bot.send_message(reply_chat_id, t("pickup_location", lang))
            await bot.send_location(reply_chat_id, latitude=PICKUP_LATITUDE, longitude=PICKUP_LONGITUDE)
        except Exception:
            logger.exception("Failed to send pickup location to chat %s", reply_chat_id)
    else:
        await bot.send_message(reply_chat_id, t("dates_taken_canceled", lang, order_id=order_id))


async def _handle_receipt_upload(
    message: Message, bot: Bot, state: FSMContext, *, file_id: str, is_document: bool
) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id
    lang = await fetch_user_language(user_id)

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                get_user_by_id_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    user_payload = await resp.json()
                    if user_payload.get("is_banned"):
                        await message.answer(t("banned_notice", lang, manager=MANAGER_USERNAME))
                        return

            async with session.get(
                get_all_orders_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status != HTTPStatus.OK:
                    await message.answer(t("service_unavailable", lang))
                    return
                orders: list[dict] = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Backend request failed fetching orders for user_id=%s", user_id)
        await message.answer(t("service_unavailable", lang))
        return
    except Exception:
        logger.exception("Unexpected error fetching orders for user_id=%s", user_id)
        await message.answer(t("unexpected_error", lang))
        return

    pending = sorted(
        [o for o in orders if o.get("status") == "created"],
        key=lambda o: o.get("order_date", ""),
        reverse=True,
    )

    if not pending:
        await message.answer(t("no_pending_orders", lang))
        return

    if len(pending) == 1:
        await _process_receipt(
            bot,
            reply_chat_id=message.chat.id,
            from_user_id=user_id,
            from_first_name=message.from_user.first_name,
            from_username=message.from_user.username,
            file_id=file_id,
            is_document=is_document,
            order=pending[0],
        )
        return

    # Multiple orders awaiting payment — don't guess which one the receipt is
    # for (misattributing a payment is a real mistake, not a cosmetic one).
    # Ask the client, then process the chosen order the same way as above.
    await state.update_data(pending_receipt_file_id=file_id, pending_receipt_is_document=is_document)
    builder = InlineKeyboardBuilder()
    for o in pending:
        builder.button(
            text=t("receipt_order_button", lang, order_id=o["order_id"], price=fmt_price(o["total_price"])),
            callback_data=f"receipt_order:{o['order_id']}",
        )
    builder.adjust(1)
    await message.answer(t("receipt_which_order", lang), reply_markup=builder.as_markup())


@router.message(F.photo)
async def handle_receipt_photo(message: Message, bot: Bot, state: FSMContext) -> None:
    await _handle_receipt_upload(message, bot, state, file_id=message.photo[-1].file_id, is_document=False)


@router.message(F.document)
async def handle_receipt_document(message: Message, bot: Bot, state: FSMContext) -> None:
    # Covers PDFs and images sent "as file" (uncompressed) — some phones/apps
    # default to this for screenshots, and F.photo never fires for them.
    if not message.document:
        return
    await _handle_receipt_upload(message, bot, state, file_id=message.document.file_id, is_document=True)


@router.callback_query(F.data.startswith("receipt_order:"))
async def handle_receipt_order_choice(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    if not callback.from_user or not callback.data:
        return

    order_id = int(callback.data.split(":")[1])
    lang = await fetch_user_language(callback.from_user.id)
    data = await state.get_data()
    file_id = data.get("pending_receipt_file_id")
    is_document = bool(data.get("pending_receipt_is_document"))

    if not file_id:
        await callback.answer(t("receipt_not_found", lang), show_alert=True)
        return

    await callback.answer()
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
                if resp.status != HTTPStatus.OK:
                    await bot.send_message(callback.from_user.id, t("service_unavailable", lang))
                    return
                order = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Failed to fetch order %s for receipt choice", order_id)
        await bot.send_message(callback.from_user.id, t("service_unavailable", lang))
        return

    # The order id comes from callback_data — confirm it's actually this user's
    # order before auto-confirming it via the internal token (don't trust the id).
    if order.get("user_id") != callback.from_user.id:
        await bot.send_message(callback.from_user.id, t("receipt_not_found", lang))
        return

    await state.update_data(pending_receipt_file_id=None, pending_receipt_is_document=None)
    await _process_receipt(
        bot,
        reply_chat_id=callback.from_user.id,
        from_user_id=callback.from_user.id,
        from_first_name=callback.from_user.first_name,
        from_username=callback.from_user.username,
        file_id=file_id,
        is_document=is_document,
        order=order,
    )


async def _resolve_and_send(target_raw: str, text: str) -> tuple[bool, str]:
    """Send a text message to an arbitrary user by @username or numeric id.

    Returns (success, label) where label is the resolved target (for a
    confirmation message) on success, or the error string on failure.
    """
    # Resolve target → Telegram chat id or username string
    if target_raw.lstrip("-").isdigit():
        target: int | str = int(target_raw)
        label = str(target)
    elif target_raw.startswith("@"):
        target = target_raw          # aiogram accepts "@username" directly
        label = target_raw
    else:
        target = f"@{target_raw}"
        label = target

    try:
        await bot.send_message(target, text)
        return True, label
    except Exception as e:
        return False, str(e)


@router.message(Command("send"))
async def handle_send(message: Message) -> None:
    if not message.from_user:
        return

    from src.handlers.admin_callbacks import _is_admin
    if not await _is_admin(message.from_user.id):
        await message.answer("Эта команда доступна только администраторам.")
        return

    # Expected: /send @username text  OR  /send 123456789 text
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "/send @username текст\n"
            "/send user_id текст"
        )
        return

    ok, result = await _resolve_and_send(args[1], args[2])
    if ok:
        await message.answer(f"✅ Сообщение отправлено → {result}")
    else:
        await message.answer(f"❌ Не удалось отправить: {result}")


class SendClientMessage(StatesGroup):
    waiting_target = State()
    waiting_text = State()


_BACK_TO_TARGET_LABEL = "🔙 Изменить получателя"


def _cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=CANCEL_LABEL)]], resize_keyboard=True)


def _back_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=_BACK_TO_TARGET_LABEL), KeyboardButton(text=CANCEL_LABEL)]],
        resize_keyboard=True,
    )


async def _back_to_admin_menu(message: Message, text: str) -> None:
    from src.handlers.admin_callbacks import _is_admin

    is_admin = await _is_admin(message.from_user.id) if message.from_user else False
    await message.answer(
        text,
        reply_markup=build_main_menu(is_admin=is_admin, lang="ru", admin_calendar_url=admin_calendar_url),
    )


@router.message(F.text == MENU_SEND, StateFilter(None))
async def menu_send_start(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return

    from src.handlers.admin_callbacks import _is_admin
    if not await _is_admin(message.from_user.id):
        await message.answer(
            "Эта команда доступна только администраторам.",
            reply_markup=build_main_menu(is_admin=False, lang="ru", admin_calendar_url=admin_calendar_url),
        )
        return

    await state.set_state(SendClientMessage.waiting_target)
    await message.answer("Кому написать? Пришлите @username или user_id.", reply_markup=_cancel_keyboard())


@router.message(SendClientMessage.waiting_target, F.text == CANCEL_LABEL)
async def menu_send_cancel_at_target(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _back_to_admin_menu(message, "Отменено.")


@router.message(SendClientMessage.waiting_target, F.text)
async def menu_send_target(message: Message, state: FSMContext) -> None:
    await state.update_data(send_target=(message.text or "").strip())
    await state.set_state(SendClientMessage.waiting_text)
    await message.answer("Что написать?", reply_markup=_back_cancel_keyboard())


@router.message(SendClientMessage.waiting_text, F.text == CANCEL_LABEL)
async def menu_send_cancel_at_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _back_to_admin_menu(message, "Отменено.")


@router.message(SendClientMessage.waiting_text, F.text == _BACK_TO_TARGET_LABEL)
async def menu_send_back_to_target(message: Message, state: FSMContext) -> None:
    await state.set_state(SendClientMessage.waiting_target)
    await message.answer("Кому написать? Пришлите @username или user_id.", reply_markup=_cancel_keyboard())


@router.message(SendClientMessage.waiting_text, F.text)
async def menu_send_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target_raw = data.get("send_target", "")
    await state.clear()

    ok, result = await _resolve_and_send(target_raw, message.text or "")

    from src.handlers.admin_callbacks import _is_admin

    is_admin = await _is_admin(message.from_user.id) if message.from_user else False
    reply_markup = build_main_menu(is_admin=is_admin, lang="ru", admin_calendar_url=admin_calendar_url)
    if ok:
        await message.answer(f"✅ Отправлено → {result}", reply_markup=reply_markup)
    else:
        await message.answer(f"❌ Не удалось отправить: {result}", reply_markup=reply_markup)
