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


async def _handle_new_order(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    from src.handlers.admin_callbacks import send_order_to_admins
    asyncio.create_task(send_order_to_admins(order_id))
    return web.Response(text="ok")


async def _handle_client_order_created(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_client_created(order_id))
    return web.Response(text="ok")


async def _handle_pickup_reminder(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_pickup(order_id))
    return web.Response(text="ok")


async def _handle_return_reminder(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        order_id = _order_id_from(data)
    except Exception:
        return web.Response(status=400, text="invalid payload")

    asyncio.create_task(_notify_return(order_id))
    return web.Response(text="ok")


async def _fetch_order(order_id: int) -> dict | None:
    from src.config import REQUEST_TIMEOUT, get_order_url
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}") as resp:
                if resp.status != HTTPStatus.OK:
                    logger.warning("Could not fetch order %s: status=%s", order_id, resp.status)
                    return None
                return await resp.json()
    except Exception:
        logger.exception("Failed to fetch order %s", order_id)
        return None


async def _notify_client_created(order_id: int) -> None:
    from src.config import DEPOSIT_AMOUNT, PAYMENT_CARD_NUMBER, bot
    order = await _fetch_order(order_id)
    if not order:
        return

    # deposit = round(order["total_price"] * DEPOSIT_PERCENT / 100)  # фиксированная сумма ниже
    deposit = DEPOSIT_AMOUNT
    text = (
        f"✅ <b>Ваш заказ #{order_id} создан!</b>\n\n"
        f"Для подтверждения переведите предоплату <b>{deposit:,} сум</b> на карту:\n"
        f"💳 <code>{PAYMENT_CARD_NUMBER}</code>\n\n"
        f"После оплаты отправьте фото чека в этот чат."
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


async def run_http_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))
    app.router.add_post("/notify/new_order", _handle_new_order)
    app.router.add_post("/notify/client_order_created", _handle_client_order_created)
    app.router.add_post("/notify/pickup_reminder", _handle_pickup_reminder)
    app.router.add_post("/notify/return_reminder", _handle_return_reminder)

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