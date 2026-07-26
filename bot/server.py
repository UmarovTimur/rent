# server.py
from aiohttp import web
import asyncio
import html
import logging
import os
from datetime import datetime, timedelta
from http import HTTPStatus

import aiohttp

from src.config import (
    CARD_NUMBER_DISPLAY,
    DEPOSIT_AMOUNT,
    INTERNAL_API_TOKEN,
    INTERNAL_HEADERS,
    PICKUP_ADDRESS,
    REQUEST_TIMEOUT,
    bot,
    fmt_price,
    get_order_url,
)
from src.i18n import status_label, t
from src.order_items import format_order_items
from src.user_lang import fetch_user_language

logger = logging.getLogger(__name__)


def _order_id_from(data: dict) -> int:
    return int(data["order_id"])


def _authorized(request: web.Request) -> bool:
    """Require the shared internal token — fails closed (rejects) if it isn't
    configured, matching the backend's require_internal. INTERNAL_API_TOKEN is
    documented as required in .env.example; an unset token means misconfiguration,
    not "no auth needed".
    """
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
    order = await _fetch_order(order_id)
    if not order:
        return
    lang = await fetch_user_language(order["user_id"])

    # Rental window across all items (earliest start / latest end) → pickup
    # and return datetimes, displayed in local Uzbekistan time (UTC+5).
    rental_starts = [i["rental_start"] for i in order.get("items", []) if i.get("rental_start")]
    rental_ends = [i["rental_end"] for i in order.get("items", []) if i.get("rental_end")]
    pickup_line = ""
    if rental_starts:
        dt = datetime.fromisoformat(min(rental_starts).replace("Z", "+00:00")) + timedelta(hours=5)
        pickup_line = t("pickup_date", lang, dt=dt.strftime("%d.%m.%Y %H:%M"))
    return_line = ""
    if rental_ends:
        dt = datetime.fromisoformat(max(rental_ends).replace("Z", "+00:00")) + timedelta(hours=5)
        return_line = t("return_date", lang, dt=dt.strftime("%d.%m.%Y %H:%M"))

    items_text = format_order_items(order.get("items", []))
    items_block = t("order_items_header", lang, items=items_text) if items_text else ""
    discount = order.get("discount") or 0
    discount_line = t("coins_redeemed", lang, amount=fmt_price(discount)) if discount > 0 else ""
    text = (
        t("order_created", lang, order_id=order_id)
        + pickup_line
        + return_line
        + items_block
        + discount_line
        + t("pickup_address", lang, address=PICKUP_ADDRESS)
        + t("deposit_instructions", lang, deposit=fmt_price(DEPOSIT_AMOUNT))
        + t("deposit_card", lang, card_number=CARD_NUMBER_DISPLAY)
        + t("send_receipt_hint", lang)
    )
    try:
        await bot.send_message(order["user_id"], text)
    except Exception:
        logger.exception("Failed to send client_order_created to user %s", order.get("user_id"))


async def _notify_pickup(order_id: int) -> None:
    order = await _fetch_order(order_id)
    if not order:
        return

    client_text = t("pickup_reminder", await fetch_user_language(order["user_id"]), order_id=order_id)
    admin_text = (
        f"⏰ <b>Напоминание о выдаче заказа #{order_id}</b>\n"
        f"👤 {html.escape(str(order.get('first_name') or '—'))} | 📞 {html.escape(str(order.get('phone') or '—'))}\n"
        f"Клиент заберёт заказ через ~2 часа."
    )
    try:
        await bot.send_message(order["user_id"], client_text)
    except Exception:
        logger.exception("Failed to send pickup reminder to user %s", order.get("user_id"))

    from src.handlers.admin_callbacks import get_admin_recipients

    for admin_id in await get_admin_recipients():
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            logger.exception("Failed to send pickup reminder to admin %s", admin_id)


async def _notify_return(order_id: int) -> None:
    order = await _fetch_order(order_id)
    if not order:
        return

    client_text = t("return_reminder", await fetch_user_language(order["user_id"]), order_id=order_id)
    admin_text = (
        f"⏰ <b>Напоминание о возврате заказа #{order_id}</b>\n"
        f"👤 {html.escape(str(order.get('first_name') or '—'))} | 📞 {html.escape(str(order.get('phone') or '—'))}\n"
        f"Клиент должен вернуть заказ через ~2 часа."
    )
    try:
        await bot.send_message(order["user_id"], client_text)
    except Exception:
        logger.exception("Failed to send return reminder to user %s", order.get("user_id"))

    from src.handlers.admin_callbacks import get_admin_recipients

    for admin_id in await get_admin_recipients():
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            logger.exception("Failed to send return reminder to admin %s", admin_id)


async def _notify_status_changed(order_id: int) -> None:
    order = await _fetch_order(order_id)
    if not order:
        return

    lang = await fetch_user_language(order["user_id"])
    label = status_label(order.get("status", ""), lang)
    text = t("status_changed", lang, order_id=order_id, status=label)
    try:
        await bot.send_message(order["user_id"], text)
    except Exception:
        logger.exception("Failed to send status_changed notification to user %s", order.get("user_id"))


async def _notify_hold_expired_cancelled(order_id: int) -> None:
    order = await _fetch_order(order_id)
    if not order:
        return

    client_text = t("hold_expired", await fetch_user_language(order["user_id"]), order_id=order_id)
    try:
        await bot.send_message(order["user_id"], client_text)
    except Exception:
        logger.exception("Failed to notify user %s about hold-expired cancellation", order.get("user_id"))

    admin_text = (
        f"⏱ <b>Заказ #{order_id} автоматически отменён</b>\n"
        f"👤 {html.escape(str(order.get('first_name') or '—'))} | 📞 {html.escape(str(order.get('phone') or '—'))}\n"
        f"Причина: не оплачен за 10 минут, даты заняты другим заказом."
    )

    from src.handlers.admin_callbacks import get_admin_recipients

    for admin_id in await get_admin_recipients():
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            logger.exception("Failed to notify admin %s about hold-expired cancellation for order %s", admin_id, order_id)


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