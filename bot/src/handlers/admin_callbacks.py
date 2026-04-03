import asyncio
import logging
from http import HTTPStatus

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import (
    REQUEST_TIMEOUT,
    bot,
    change_status_url,
    get_admins_url,
    get_all_orders_url,
    get_order_url,
    get_user_by_id_url,
)

router = Router(name="admin_callbacks")
logger = logging.getLogger(__name__)

# Statuses that still hold products reserved
_ACTIVE_STATUSES = {"created", "in_progress", "taken"}

_STATUS_LABEL = {
    "created": "🆕 Создан",
    "in_progress": "▶️ В работе",
    "taken": "📦 Принят",
    "paused": "⏸ Пауза",
    "completed": "✅ Закрыт",
    "canceled": "❌ Отменён",
}


# ─── Keyboard ────────────────────────────────────────────────────────────────

def _order_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status in _ACTIVE_STATUSES:
        builder.button(text="✅ Одобрить", callback_data=f"order:approve:{order_id}")
        builder.button(text="⏸ Пауза", callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
        builder.adjust(3)
    elif status == "paused":
        builder.button(text="▶️ Возобновить", callback_data=f"order:approve:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
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
    lines.append(f"💰 Итого: {order['total_price']} ₽")

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
            line = f"  • {name} ×{qty} — {price * qty} ₽"
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

        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, text, reply_markup=keyboard)
            except Exception:
                logger.exception("Failed to send order notification to admin %s", admin_id)
    except Exception:
        logger.exception("send_order_to_admins failed for order_id=%s", order_id)


# ─── Callback handler ────────────────────────────────────────────────────────

_ACTION_STATUS = {
    "approve": "in_progress",
    "pause": "paused",
    "close": "completed",
    "reopen": "in_progress",
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

    text = _format_order(order)
    keyboard = _order_keyboard(order_id, new_status)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ─── /orders admin command ───────────────────────────────────────────────────

@router.message(Command("orders"))
async def get_active_orders(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(get_user_by_id_url, params={"user_id": user_id}) as resp:
            if resp.status != HTTPStatus.OK:
                await message.answer("Нет доступа.")
                return
            user_data = await resp.json()

        if not user_data.get("is_admin"):
            await message.answer("Эта команда доступна только администраторам.")
            return

        async with session.get(get_all_orders_url) as resp:
            if resp.status != HTTPStatus.OK:
                await message.answer("Не удалось получить заказы.")
                return
            all_orders: list[dict] = await resp.json()

    active = [o for o in all_orders if o.get("status") in _ACTIVE_STATUSES]

    if not active:
        await message.answer("Активных заказов нет.")
        return

    for order in active:
        text = _format_order(order)
        keyboard = _order_keyboard(order["order_id"], order["status"])
        await message.answer(text, reply_markup=keyboard)
        await asyncio.sleep(0.05)  # avoid Telegram flood limits
