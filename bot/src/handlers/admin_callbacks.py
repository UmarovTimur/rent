import asyncio
import logging
from http import HTTPStatus

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import (
    ADMIN_CHAT_ID,
    REQUEST_TIMEOUT,
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
    "taken": "📦 Принят",
    "paused": "⏸ Пауза",
    "completed": "✅ Закрыт",
    "canceled": "❌ Отменён",
}


# ─── Admin check ─────────────────────────────────────────────────────────────

async def _is_admin(user_id: int) -> bool:
    if ADMIN_CHAT_ID and user_id == ADMIN_CHAT_ID:
        return True
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(get_user_by_id_url, params={"user_id": user_id}) as resp:
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
    builder.button(text="📦 Принят",     callback_data="filter:taken")
    builder.button(text="⏸ Пауза",      callback_data="filter:paused")
    builder.button(text="✅ Закрыт",     callback_data="filter:completed")
    builder.button(text="❌ Отменён",    callback_data="filter:canceled")
    builder.button(text="🔥 Активные",  callback_data="filter:active")
    builder.button(text="📋 Все",        callback_data="filter:all")
    builder.adjust(3, 3, 2)
    return builder.as_markup()


def _order_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status in _ACTIVE_STATUSES:
        builder.button(text="✅ Одобрить", callback_data=f"order:approve:{order_id}")
        builder.button(text="⏸ Пауза",    callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
        builder.adjust(3)
    elif status == "paused":
        builder.button(text="▶️ Возобновить", callback_data=f"order:approve:{order_id}")
        builder.button(text="🔒 Закрыть",     callback_data=f"order:close:{order_id}")
        builder.adjust(2)
    elif status == "completed":
        builder.button(text="↩️ Отменить закрытие", callback_data=f"order:reopen:{order_id}")
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
            async with session.get(f"{get_order_url}/{order_id}") as resp:
                if resp.status != HTTPStatus.OK:
                    logger.warning("Could not fetch order %s for notification: %s", order_id, resp.status)
                    return
                order = await resp.json()

            async with session.get(get_admins_url) as resp:
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
    "approve": "in_progress",
    "pause":   "paused",
    "close":   "completed",
    "reopen":  "in_progress",
}


@router.callback_query(F.data.startswith("order:"))
async def handle_order_action(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверный формат", show_alert=True)
        return

    _, action, order_id_str = parts
    if action not in _ACTION_STATUS:
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    order_id = int(order_id_str)
    new_status = _ACTION_STATUS[action]

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.patch(
            f"{change_status_url}/{order_id}",
            params={"status": new_status},
        ) as resp:
            if resp.status not in {HTTPStatus.NO_CONTENT, HTTPStatus.OK}:
                await callback.answer("Ошибка при смене статуса", show_alert=True)
                return

        async with session.get(f"{get_order_url}/{order_id}") as resp:
            if resp.status != HTTPStatus.OK:
                await callback.answer("Статус обновлён")
                return
            order = await resp.json()

    if action == "approve":
        try:
            await bot.send_message(
                order["user_id"],
                f"✅ <b>Ваш заказ #{order_id} подтверждён!</b> Ждём вас.",
            )
        except Exception:
            logger.exception("Failed to notify client %s about order %s approval", order.get("user_id"), order_id)

    text = _format_order(order)
    keyboard = _order_keyboard(order_id, new_status)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


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
        async with session.get(get_all_orders_url) as resp:
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
