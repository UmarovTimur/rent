import asyncio
import logging
from http import HTTPStatus

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import (
    ADMIN_CHAT_ID,
    INTERNAL_HEADERS,
    REQUEST_TIMEOUT,
    admin_calendar_url,
    bot,
    change_status_url,
    fmt_price,
    get_admins_url,
    get_all_orders_url,
    get_order_url,
    get_user_by_id_url,
)

router = Router(name="admin_callbacks")
logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {"created", "in_progress", "taken"}
_MAX_ORDERS = 20

_STATUS_LABEL = {
    "created": "🆕 Создан",
    "in_progress": "▶️ В работе",
    "taken": "📦 Отдано клиенту",
    "paused": "⏸ Пауза",
    "returned": "✅ Возвращён",
    "completed": "🚫 Закрыт (неуспешно)",
    "canceled": "❌ Отменён",
}


# ─── Admin check ─────────────────────────────────────────────────────────────

async def _is_admin(user_id: int) -> bool:
    if ADMIN_CHAT_ID and user_id == ADMIN_CHAT_ID:
        return True
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                get_user_by_id_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    data = await resp.json()
                    return bool(data.get("is_admin"))
    except Exception:
        logger.exception("Admin check failed for user_id=%s", user_id)
    return False


# ─── Keyboards ───────────────────────────────────────────────────────────────

def _filter_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Создан",     callback_data="filter:created")
    builder.button(text="▶️ В работе",   callback_data="filter:in_progress")
    builder.button(text="📦 Отдано",     callback_data="filter:taken")
    builder.button(text="⏸ Пауза",      callback_data="filter:paused")
    builder.button(text="✅ Возвращён",  callback_data="filter:returned")
    builder.button(text="🚫 Закрыт",     callback_data="filter:completed")
    builder.button(text="❌ Отменён",    callback_data="filter:canceled")
    builder.button(text="🔥 Активные",  callback_data="filter:active")
    builder.button(text="📋 Все",        callback_data="filter:all")
    builder.adjust(3, 3, 3)
    return builder.as_markup()


def _order_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status == "created":
        # Only a brand-new order can be approved.
        builder.button(text="✅ Одобрить", callback_data=f"order:approve:{order_id}")
        builder.button(text="⏸ Пауза",    callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
        builder.adjust(3)
    elif status == "in_progress":
        # Approved and holding the slot — next physical step is handing the gear over.
        builder.button(text="📦 Отдал",   callback_data=f"order:handover:{order_id}")
        builder.button(text="⏸ Пауза",    callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
        builder.adjust(3)
    elif status == "taken":
        # Gear is with the client — next physical step is getting it back.
        # "Отменить отдал" covers marking it as taken by mistake.
        builder.button(text="✅ Вернули",       callback_data=f"order:return:{order_id}")
        builder.button(text="↩️ Отменить отдал", callback_data=f"order:undo_handover:{order_id}")
        builder.button(text="⏸ Пауза",          callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть",       callback_data=f"order:close:{order_id}")
        builder.adjust(2, 2)
    elif status == "paused":
        builder.button(text="▶️ Возобновить", callback_data=f"order:approve:{order_id}")
        builder.button(text="🔒 Закрыть",     callback_data=f"order:close:{order_id}")
        builder.adjust(2)
    elif status == "returned":
        # Undo goes back to "taken" (a return always follows a handover) — not
        # a full reopen, so admins correcting a mis-click keep the handover marker.
        builder.button(text="↩️ Отменить возврат", callback_data=f"order:undo_return:{order_id}")
        builder.adjust(1)
    elif status == "completed":
        builder.button(text="↩️ Открыть заново", callback_data=f"order:reopen:{order_id}")
        builder.adjust(1)
    return builder.as_markup()


# ─── Message formatter ───────────────────────────────────────────────────────

def _format_order(order: dict) -> str:
    lines = [
        f"<b>Заказ #{order['order_id']}</b>",
        f"📅 {order['order_date'][:16].replace('T', ' ')}",
    ]
    if order.get("first_name"):
        lines.append(f"👤 {order['first_name']}")
    if order.get("phone"):
        lines.append(f"📞 {order['phone']}")
    if order.get("address"):
        lines.append(f"📍 {order['address']}")

    payment = "карта" if order.get("payment_option") == "card" else "наличные"
    lines.append(f"💳 Оплата: {payment}")
    lines.append(f"💰 Итого: {fmt_price(order['total_price'])} сум")

    if order.get("comment"):
        lines.append(f"💬 {order['comment']}")

    items = order.get("items", [])
    if items:
        lines.append("")
        lines.append("📦 <b>Состав:</b>")
        for item in items:
            name = item.get("product_name") or f"Товар #{item['product_id']}"
            qty = item["quantity"]
            price = item["unit_price"]
            line = f"  • {name} ×{qty} — {fmt_price(price * qty)} сум"
            if item.get("rental_start") and item.get("rental_end"):
                start = item["rental_start"][:16].replace("T", " ")
                end = item["rental_end"][:16].replace("T", " ")
                line += f"\n    📆 {start} — {end}"
            lines.append(line)

    status_label = _STATUS_LABEL.get(order.get("status", ""), order.get("status", ""))
    lines.append(f"\nСтатус: {status_label}")
    return "\n".join(lines)


# ─── Notification sender (called from server.py) ─────────────────────────────

async def send_order_to_admins(order_id: int) -> None:
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
                if resp.status != HTTPStatus.OK:
                    logger.warning("Could not fetch order %s for notification: %s", order_id, resp.status)
                    return
                order = await resp.json()

            async with session.get(get_admins_url, headers=INTERNAL_HEADERS) as resp:
                if resp.status != HTTPStatus.OK:
                    logger.warning("Could not fetch admin list: %s", resp.status)
                    return
                admin_ids: list[int] = await resp.json()

        text = _format_order(order)
        keyboard = _order_keyboard(order_id, order["status"])

        recipients = list(admin_ids)
        if ADMIN_CHAT_ID and ADMIN_CHAT_ID not in recipients:
            recipients.append(ADMIN_CHAT_ID)

        for admin_id in recipients:
            try:
                await bot.send_message(admin_id, text, reply_markup=keyboard)
            except Exception:
                logger.exception("Failed to send order notification to admin %s", admin_id)
    except Exception:
        logger.exception("send_order_to_admins failed for order_id=%s", order_id)


# ─── Order action callback ────────────────────────────────────────────────────

_ACTION_STATUS = {
    "approve":       "in_progress",
    "pause":         "paused",
    "close":         "completed",
    "reopen":        "in_progress",
    "handover":      "taken",       # "Отдал" — gear physically given to the client
    "return":        "returned",    # "Вернули" — gear physically given back, successful outcome
    "undo_handover": "in_progress", # mistake correction: undo "Отдал"
    "undo_return":   "taken",       # mistake correction: undo "Вернули"
}

# Only reachable from this status — guards against a stale/double-tapped
# keyboard applying an action out of order (e.g. two admins, or a leftover
# card from before a pause/reopen).
_ACTION_REQUIRES_STATUS = {
    "handover": "in_progress",
    "return": "taken",
    "undo_handover": "taken",
    "undo_return": "returned",
    "reopen": "completed",
}

# Actions where the admin is asked for a short comment explaining the change to
# the client, before it's applied. "approve" only prompts when it means resuming
# a paused order — the very first confirmation (from "created") keeps its own
# automatic "your order is confirmed" message with no prompt. "handover"/"return"
# are physical-handoff markers the client already knows about — no prompt needed.
_ACTION_VERB = {
    "pause": "приостановили",
    "close": "закрыли",
    "approve": "возобновили",
}


class OrderAction(StatesGroup):
    waiting_comment = State()


async def _apply_order_action(
    order_id: int,
    action: str,
    *,
    client_text: str | None,
    comment: str | None,
    reply_chat_id: int,
    admin_message_id: int | None,
) -> None:
    """Patch the order's status, notify the client (if client_text is given,
    with the admin's comment appended), and refresh the admin card in place.
    """
    new_status = _ACTION_STATUS[action]

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.patch(
            f"{change_status_url}/{order_id}",
            params={"status": new_status},
            headers=INTERNAL_HEADERS,
        ) as resp:
            if resp.status not in {HTTPStatus.NO_CONTENT, HTTPStatus.OK}:
                await bot.send_message(reply_chat_id, f"❌ Ошибка при смене статуса заказа #{order_id}.")
                return

        async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
            if resp.status != HTTPStatus.OK:
                await bot.send_message(reply_chat_id, "Статус обновлён.")
                return
            order = await resp.json()

    if client_text:
        text = client_text.format(order_id=order_id)
        if comment:
            text += f"\n\n💬 {comment}"
        try:
            await bot.send_message(order["user_id"], text)
        except Exception:
            logger.exception("Failed to notify client %s about order %s (%s)", order.get("user_id"), order_id, action)

    if admin_message_id:
        await _refresh_admin_card(order_id, order, new_status, reply_chat_id, admin_message_id)


async def _refresh_admin_card(
    order_id: int, order: dict, new_status: str, chat_id: int, message_id: int
) -> None:
    """Update the admin card in place after a status change.

    The card may be a plain text message (from send_order_to_admins) or a photo
    message with a caption (the receipt forwarded by _process_receipt) — Telegram
    rejects edit_message_text on a photo message ("there is no text to edit"), so
    try text first and fall back to caption, then to reply-markup-only as a last
    resort, instead of silently leaving a stale keyboard on the card.
    """
    text = _format_order(order)
    keyboard = _order_keyboard(order_id, new_status)
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
        return
    except Exception:
        pass
    try:
        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, reply_markup=keyboard)
        return
    except Exception:
        pass
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to refresh admin card for order %s", order_id)


@router.callback_query(F.data.startswith("order:"))
async def handle_order_action(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверный формат", show_alert=True)
        return

    _, action, order_id_str = parts
    if action not in _ACTION_STATUS:
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    order_id = int(order_id_str)

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
            current_status = None
            if resp.status == HTTPStatus.OK:
                current = await resp.json()
                current_status = current.get("status")

    # Guard against double-approval (fast double-tap / two admins): only a
    # "created" or "paused" order can be approved/resumed.
    if action == "approve" and current_status not in {"created", "paused"}:
        await callback.answer("Заказ уже одобрен", show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_order_keyboard(order_id, current_status or "")
            )
        return

    # Guard against a stale keyboard: "Отдал" only makes sense from in_progress,
    # "Вернули" only from taken (can't return gear that was never handed over).
    required_status = _ACTION_REQUIRES_STATUS.get(action)
    if required_status and current_status != required_status:
        await callback.answer("Статус заказа уже изменился", show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_order_keyboard(order_id, current_status or "")
            )
        return

    if not callback.message:
        return

    is_resume = action == "approve" and current_status == "paused"
    # Pause/close/resume are all "tell the client why" moments — prompt for a
    # short comment before applying. The very first confirmation (approve from
    # "created") keeps its existing automatic message and isn't prompted.
    if action in {"pause", "close"} or is_resume:
        await state.update_data(
            pending_order_id=order_id,
            pending_action=action,
            pending_chat_id=callback.message.chat.id,
            pending_message_id=callback.message.message_id,
        )
        await state.set_state(OrderAction.waiting_comment)
        await callback.answer()
        await bot.send_message(
            callback.message.chat.id,
            f"Напишите комментарий для клиента — почему заказ #{order_id} {_ACTION_VERB[action]} "
            f"(когда открыть снова и т.п.). Или отправьте «-», чтобы отправить без комментария.",
        )
        return

    direct_client_text = {
        "approve": "✅ <b>Ваш заказ #{order_id} подтверждён!</b> Ждём вас.",
        "return": "✅ <b>Заказ #{order_id} завершён.</b> Спасибо, что вернули снаряжение!",
    }.get(action)

    await _apply_order_action(
        order_id,
        action,
        client_text=direct_client_text,
        comment=None,
        reply_chat_id=callback.message.chat.id,
        admin_message_id=callback.message.message_id,
    )
    await callback.answer()


@router.message(OrderAction.waiting_comment, F.text)
async def handle_order_action_comment(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    order_id = data.get("pending_order_id")
    action = data.get("pending_action")
    admin_chat_id = data.get("pending_chat_id")
    admin_message_id = data.get("pending_message_id")
    await state.clear()

    if not order_id or not action:
        return

    comment = (message.text or "").strip()
    if comment == "-":
        comment = None

    client_text = {
        "pause": "⏸ <b>Ваш заказ #{order_id} приостановлен.</b>",
        "close": "🔒 <b>Ваш заказ #{order_id} закрыт.</b>",
        "approve": "▶️ <b>Ваш заказ #{order_id} возобновлён.</b>",
    }.get(action)

    await _apply_order_action(
        order_id,
        action,
        client_text=client_text,
        comment=comment,
        reply_chat_id=admin_chat_id or message.chat.id,
        admin_message_id=admin_message_id,
    )
    await message.answer(f"Готово: заказ #{order_id} обновлён.")


# ─── Filter callback ─────────────────────────────────────────────────────────

def _pluralize_orders(n: int) -> str:
    if 11 <= n % 100 <= 19:
        return f"{n} заказов"
    r = n % 10
    if r == 1:
        return f"{n} заказ"
    if 2 <= r <= 4:
        return f"{n} заказа"
    return f"{n} заказов"


@router.callback_query(F.data.startswith("filter:"))
async def handle_filter(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id if callback.from_user else None
    if not user_id or not await _is_admin(user_id):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()

    status_filter = callback.data.split(":")[1]

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(get_all_orders_url, headers=INTERNAL_HEADERS) as resp:
            if resp.status != HTTPStatus.OK:
                await callback.message.edit_text("❌ Не удалось получить заказы.", reply_markup=_filter_keyboard())
                return
            all_orders: list[dict] = await resp.json()

    if status_filter == "all":
        filtered = all_orders
        label = "Все заказы"
    elif status_filter == "active":
        filtered = [o for o in all_orders if o.get("status") in _ACTIVE_STATUSES]
        label = "Активные"
    else:
        filtered = [o for o in all_orders if o.get("status") == status_filter]
        label = _STATUS_LABEL.get(status_filter, status_filter)

    filtered.sort(key=lambda o: o.get("order_date", ""), reverse=True)
    total = len(filtered)
    shown = filtered[:_MAX_ORDERS]

    if not shown:
        await callback.message.edit_text(
            f"📋 {label}: заказов нет.",
            reply_markup=_filter_keyboard(),
        )
        return

    suffix = f" (показаны последние {_MAX_ORDERS})" if total > _MAX_ORDERS else ""
    await callback.message.edit_text(
        f"📋 {label}: {_pluralize_orders(total)}{suffix}",
        reply_markup=_filter_keyboard(),
    )

    for order in shown:
        text = _format_order(order)
        keyboard = _order_keyboard(order["order_id"], order["status"])
        await callback.message.answer(text, reply_markup=keyboard)
        await asyncio.sleep(0.05)


# ─── /orders command ─────────────────────────────────────────────────────────

@router.message(Command("orders"))
async def orders_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not await _is_admin(user_id):
        await message.answer("Эта команда доступна только администраторам.")
        return
    await message.answer("📋 Выберите фильтр заказов:", reply_markup=_filter_keyboard())


# ─── /admin_calendar command ──────────────────────────────────────────────────

@router.message(Command("admin_calendar"))
async def admin_calendar(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not await _is_admin(user_id):
        await message.answer("Эта команда доступна только администраторам.")
        return
    if not admin_calendar_url:
        await message.answer("Календарь не настроен: не задан FRONTEND_URL.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Открыть календарь аренды", web_app=WebAppInfo(url=admin_calendar_url))
    await message.answer("Календарь аренды:", reply_markup=builder.as_markup())
