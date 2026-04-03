import logging
import os

import aiohttp

logger = logging.getLogger(__name__)

_BOT_INTERNAL_URL = os.getenv("BOT_INTERNAL_URL", "http://bot:8001").rstrip("/")
_TIMEOUT = aiohttp.ClientTimeout(total=5)


async def notify_new_order(order_id: int) -> None:
    url = f"{_BOT_INTERNAL_URL}/notify/new_order"
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(url, json={"order_id": order_id}) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "Bot notification returned unexpected status=%s body=%s",
                        resp.status,
                        body[:200],
                    )
    except Exception:
        logger.exception("Failed to notify bot about new order %s", order_id)
