import asyncio
import logging
from http import HTTPStatus

import aiohttp
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import (
    ADMIN_CHAT_ID,
    INTERNAL_HEADERS,
    REQUEST_TIMEOUT,
    bot,
    change_status_url,
    create_user_url,
    fmt_price,
    get_all_orders_url,
    get_order_url,
    get_user_by_id_url,
)

router = Router(name="message_handlers")
logger = logging.getLogger(__name__)
SERVICE_UNAVAILABLE_TEXT = "Сервис временно недоступен. Пожалуйста, попробуйте позже."
UNEXPECTED_ERROR_TEXT = "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
WELCOME_TEXT = "Добро пожаловать! Нажмите на кнопку «Магазин», чтобы открыть мини-приложение."


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
    await message.answer(WELCOME_TEXT)


async def _process_receipt(
    bot: Bot,
    *,
    reply_chat_id: int,
    from_user_id: int,
    from_first_name: str | None,
    from_username: str | None,
    photo_file_id: str,
    order: dict,
) -> None:
    """Forward a receipt photo to admins and auto-confirm the given order's
    payment right away — no admin click needed. This makes the hold permanent
    (see RentalService.update_rental_status, which re-checks availability on
    this exact transition). If someone else has since taken the slot, the
    confirmation is rejected (409): cancel this order and tell the client
    directly instead of leaving it stuck.
    """
    order_id = order["order_id"]
    client_label = f"@{from_username}" if from_username else f"ID: {from_user_id}"

    items = order.get("items", [])
    item_lines = []
    for i in items:
        name = i.get("product_name") or f"Товар #{i['product_id']}"
        item_lines.append(f"  • {name} ×{i['quantity']} — {fmt_price(i['unit_price'] * i['quantity'])} сум")
    items_text = "\n".join(item_lines)

    caption = (
        f"📎 <b>Чек об оплате депозита</b>\n"
        f"Клиент: {from_first_name or '—'} ({client_label})\n"
        f"Заказ <b>#{order_id}</b> | {fmt_price(order['total_price'])} сум\n"
    )
    if items_text:
        caption += f"\n<b>Состав:</b>\n{items_text}"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить заказ", callback_data=f"order:approve:{order_id}")
    keyboard: InlineKeyboardMarkup = builder.as_markup()

    if ADMIN_CHAT_ID:
        try:
            await bot.send_photo(ADMIN_CHAT_ID, photo_file_id, caption=caption, reply_markup=keyboard)
        except Exception:
            logger.exception("Failed to forward receipt to admin chat %s", ADMIN_CHAT_ID)

    await bot.send_message(reply_chat_id, "Чек получен, проверяем оплату...")
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.patch(
                f"{change_status_url}/{order_id}",
                params={"status": "in_progress"},
                headers=INTERNAL_HEADERS,
            ) as resp:
                confirmed = resp.status in {HTTPStatus.NO_CONTENT, HTTPStatus.OK}

        if confirmed:
            await bot.send_message(
                reply_chat_id, f"✅ Оплата по заказу #{order_id} подтверждена, бронь закреплена за вами."
            )
        else:
            async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
                async with session.patch(
                    f"{change_status_url}/{order_id}",
                    params={"status": "canceled"},
                    headers=INTERNAL_HEADERS,
                ):
                    pass
            await bot.send_message(
                reply_chat_id,
                f"❌ К сожалению, эти даты по заказу #{order_id} уже забронировал другой клиент. "
                f"Заказ отменён — оформите новый на актуальные даты, если снаряжение всё ещё нужно.",
            )
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Failed to auto-confirm payment for order %s", order_id)


@router.message(F.photo)
async def handle_receipt_photo(message: Message, bot: Bot, state: FSMContext) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                get_all_orders_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status != HTTPStatus.OK:
                    await message.answer(SERVICE_UNAVAILABLE_TEXT)
                    return
                orders: list[dict] = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Backend request failed fetching orders for user_id=%s", user_id)
        await message.answer(SERVICE_UNAVAILABLE_TEXT)
        return
    except Exception:
        logger.exception("Unexpected error fetching orders for user_id=%s", user_id)
        await message.answer(UNEXPECTED_ERROR_TEXT)
        return

    pending = sorted(
        [o for o in orders if o.get("status") == "created"],
        key=lambda o: o.get("order_date", ""),
        reverse=True,
    )

    if not pending:
        await message.answer("У вас нет заказов, ожидающих подтверждения оплаты.")
        return

    photo_file_id = message.photo[-1].file_id

    if len(pending) == 1:
        await _process_receipt(
            bot,
            reply_chat_id=message.chat.id,
            from_user_id=user_id,
            from_first_name=message.from_user.first_name,
            from_username=message.from_user.username,
            photo_file_id=photo_file_id,
            order=pending[0],
        )
        return

    # Multiple orders awaiting payment — don't guess which one the receipt is
    # for (misattributing a payment is a real mistake, not a cosmetic one).
    # Ask the client, then process the chosen order the same way as above.
    await state.update_data(pending_receipt_photo_id=photo_file_id)
    builder = InlineKeyboardBuilder()
    for o in pending:
        builder.button(
            text=f"Заказ #{o['order_id']} — {fmt_price(o['total_price'])} сум",
            callback_data=f"receipt_order:{o['order_id']}",
        )
    builder.adjust(1)
    await message.answer(
        "У вас несколько заказов, ожидающих оплаты. К какому из них относится этот чек?",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("receipt_order:"))
async def handle_receipt_order_choice(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    if not callback.from_user or not callback.data:
        return

    order_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    photo_file_id = data.get("pending_receipt_photo_id")

    if not photo_file_id:
        await callback.answer("Чек не найден, отправьте его ещё раз.", show_alert=True)
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
                    await bot.send_message(callback.from_user.id, SERVICE_UNAVAILABLE_TEXT)
                    return
                order = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Failed to fetch order %s for receipt choice", order_id)
        await bot.send_message(callback.from_user.id, SERVICE_UNAVAILABLE_TEXT)
        return

    await state.update_data(pending_receipt_photo_id=None)
    await _process_receipt(
        bot,
        reply_chat_id=callback.from_user.id,
        from_user_id=callback.from_user.id,
        from_first_name=callback.from_user.first_name,
        from_username=callback.from_user.username,
        photo_file_id=photo_file_id,
        order=order,
    )


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

    target_raw = args[1]
    text = args[2]

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
        await message.answer(f"✅ Сообщение отправлено → {label}")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}")
