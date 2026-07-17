# server.py
from aiohttp import web
import asyncio
import logging
import os
from http import HTTPStatus

import aiohttp

logger = logging.getLogger(__name__)


def _order_id_from(data: dict) -> int:
    return int(data["order_id"])


def _authorized(request: web.Request) -> bool:
    """Require the shared internal token — fails closed (rejects) if it isn't
    configured, matching the backend's require_internal. INTERNAL_API_TOKEN is
    documented as required in .env.example; an unset token means misconfiguration,
    not "no auth needed".
    """
    from src.config import INTERNAL_API_TOKEN
    if not INTERNAL_API_TOKEN:
        return False
    return request.headers.get("X-Internal-Token") == INTERNAL_API_TOKEN


async def _handle_new_order(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(status=401, text="unauthorized")
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    from src.handlers.admin_callbacks import send_order_to_admins
    asyncio.create_task(send_order_to_admins(order_id))
    return web.Response(text="ok")


async def _handle_client_order_created(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(status=401, text="unauthorized")
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_client_created(order_id))
    return web.Response(text="ok")


async def _handle_pickup_reminder(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(status=401, text="unauthorized")
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_pickup(order_id))
    return web.Response(text="ok")


async def _handle_return_reminder(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(status=401, text="unauthorized")
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_return(order_id))
    return web.Response(text="ok")


async def _handle_status_changed(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(status=401, text="unauthorized")
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_status_changed(order_id))
    return web.Response(text="ok")


async def _handle_hold_expired_cancelled(request: web.Request) -> web.Response:
    if not _authorized(request):
        return web.Response(status=401, text="unauthorized")
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_hold_expired_cancelled(order_id))
    return web.Response(text="ok")


async def _fetch_order(order_id: int) -> dict | None:
    from src.config import INTERNAL_HEADERS, REQUEST_TIMEOUT, get_order_url
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
                if resp.status != HTTPStatus.OK:
                    logger.warning("Could not fetch order %s: status=%s", order_id, resp.status)
                    return None
                return await resp.json()
    except Exception:
        logger.exception("Failed to fetch order %s", order_id)
        return None


async def _notify_client_created(order_id: int) -> None:
    from src.config import DEPOSIT_AMOUNT, PAYMENT_CARD_NUMBER, bot, fmt_price
    from datetime import datetime, timedelta, timezone
    order = await _fetch_order(order_id)
    if not order:
        return

    # Earliest rental_start across all items → pickup datetime (UTC+5 Uzbekistan)
    rental_starts = [i["rental_start"] for i in order.get("items", []) if i.get("rental_start")]
    pickup_line = ""
    if rental_starts:
        earliest = min(rental_starts)
        dt = datetime.fromisoformat(earliest.replace("Z", "+00:00"))
        dt_uz = dt + timedelta(hours=5)
        pickup_line = f"📅 Дата получения: <b>{dt_uz.strftime('%d.%m.%Y в %H:%M')}</b>\n"

    # deposit = round(order["total_price"] * DEPOSIT_PERCENT / 100)  # фиксированная сумма ниже
    deposit = DEPOSIT_AMOUNT
    text = (
        f"✅ <b>Ваш заказ #{order_id} создан!</b>\n\n"
        f"{pickup_line}"
        f"📍 Адрес выдачи: <b>Chilonzor 3-kvartal</b>\n\n"
        f"Для подтверждения переведите предоплату <b>{fmt_price(deposit)} сум</b> на карту:\n"
        f"💳 <code>{PAYMENT_CARD_NUMBER}</code>\n\n"
        f"После оплаты отправьте фото чека в этот чат.\n\n"
        f"👨‍💼 Менеджер: @status_3"
    )
    try:
        await bot.send_message(order["user_id"], text)
    except Exception:
        logger.exception("Failed to send client_order_created to user %s", order.get("user_id"))


async def _notify_pickup(order_id: int) -> None:
    from src.config import ADMIN_CHAT_ID, bot
    order = await _fetch_order(order_id)
    if not order:
        return

    client_text = f"⏰ <b>Напоминание:</b> через ~2 часа вы должны забрать заказ <b>#{order_id}</b>."
    admin_text = (
        f"⏰ <b>Напоминание о выдаче заказа #{order_id}</b>\n"
        f"👤 {order.get('first_name', '—')} | 📞 {order.get('phone', '—')}\n"
        f"Клиент заберёт заказ через ~2 часа."
    )
    try:
        await bot.send_message(order["user_id"], client_text)
    except Exception:
        logger.exception("Failed to send pickup reminder to user %s", order.get("user_id"))
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception:
            logger.exception("Failed to send pickup reminder to admin chat %s", ADMIN_CHAT_ID)


async def _notify_return(order_id: int) -> None:
    from src.config import ADMIN_CHAT_ID, bot
    order = await _fetch_order(order_id)
    if not order:
        return

    client_text = f"⏰ <b>Напоминание:</b> через ~2 часа вы должны вернуть заказ <b>#{order_id}</b>."
    admin_text = (
        f"⏰ <b>Напоминание о возврате заказа #{order_id}</b>\n"
        f"👤 {order.get('first_name', '—')} | 📞 {order.get('phone', '—')}\n"
        f"Клиент должен вернуть заказ через ~2 часа."
    )
    try:
        await bot.send_message(order["user_id"], client_text)
    except Exception:
        logger.exception("Failed to send return reminder to user %s", order.get("user_id"))
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception:
            logger.exception("Failed to send return reminder to admin chat %s", ADMIN_CHAT_ID)


async def _notify_status_changed(order_id: int) -> None:
    from src.config import bot
    from src.handlers.admin_callbacks import _STATUS_LABEL
    order = await _fetch_order(order_id)
    if not order:
        return

    status_label = _STATUS_LABEL.get(order.get("status", ""), order.get("status", ""))
    text = f"ℹ️ <b>Статус вашего заказа #{order_id} изменён:</b> {status_label}"
    try:
        await bot.send_message(order["user_id"], text)
    except Exception:
        logger.exception("Failed to send status_changed notification to user %s", order.get("user_id"))


async def _notify_hold_expired_cancelled(order_id: int) -> None:
    from src.config import ADMIN_CHAT_ID, bot
    order = await _fetch_order(order_id)
    if not order:
        return

    client_text = (
        f"❌ <b>Заказ #{order_id} отменён.</b>\n\n"
        f"Мы не получили подтверждение оплаты вовремя, и эти даты забронировал другой клиент.\n"
        f"Если снаряжение всё ещё нужно — оформите новый заказ на актуальные даты."
    )
    try:
        await bot.send_message(order["user_id"], client_text)
    except Exception:
        logger.exception("Failed to notify user %s about hold-expired cancellation", order.get("user_id"))

    if ADMIN_CHAT_ID:
        admin_text = (
            f"⏱ <b>Заказ #{order_id} автоматически отменён</b>\n"
            f"👤 {order.get('first_name', '—')} | 📞 {order.get('phone', '—')}\n"
            f"Причина: не оплачен за 10 минут, даты заняты другим заказом."
        )
        try:
            await bot.send_message(ADMIN_CHAT_ID, admin_text)
        except Exception:
            logger.exception("Failed to notify admin chat about hold-expired cancellation for order %s", order_id)


async def run_http_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))
    app.router.add_post("/notify/new_order", _handle_new_order)
    app.router.add_post("/notify/client_order_created", _handle_client_order_created)
    app.router.add_post("/notify/pickup_reminder", _handle_pickup_reminder)
    app.router.add_post("/notify/return_reminder", _handle_return_reminder)
    app.router.add_post("/notify/status_changed", _handle_status_changed)
    app.router.add_post("/notify/hold_expired_cancelled", _handle_hold_expired_cancelled)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 8001))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"HTTP server started on port {port}")
    await asyncio.Event().wait()  # Keep running


async def start_bot():
    from src.app import start_polling
    await start_polling()  # Запуск бота через polling


async def main():
    await asyncio.gather(
        run_http_server(),
        start_bot()
    )


if __name__ == "__main__":
    asyncio.run(main())