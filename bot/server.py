# server.py
from aiohttp import web
import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def _handle_new_order(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        order_id = int(data["order_id"])
    except Exception:
        return web.Response(status=400, text="invalid payload")

    # Fire-and-forget: don't block the response while sending Telegram messages
    from src.handlers.admin_callbacks import send_order_to_admins
    asyncio.create_task(send_order_to_admins(order_id))
    return web.Response(text="ok")


async def run_http_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))
    app.router.add_post("/notify/new_order", _handle_new_order)

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