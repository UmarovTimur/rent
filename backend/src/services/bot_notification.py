import logging
import os

import aiohttp

logger = logging.getLogger(__name__)

_BOT_INTERNAL_URL = os.getenv("BOT_INTERNAL_URL", "http://bot:8001").rstrip("/")
_TIMEOUT = aiohttp.ClientTimeout(total=5)
_INTERNAL_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
_INTERNAL_HEADERS = {"X-Internal-Token": _INTERNAL_TOKEN} if _INTERNAL_TOKEN else {}


async def _post(path: str, payload: dict) -> None:
    url = f"{_BOT_INTERNAL_URL}{path}"
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(url, json=payload, headers=_INTERNAL_HEADERS) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Bot notification %s returned status=%s body=%s", path, resp.status, body[:200])
    except Exception:
        logger.exception("Failed to call bot endpoint %s payload=%s", path, payload)


async def notify_new_order(order_id: int) -> None:
    await _post("/notify/new_order", {"order_id": order_id})


async def notify_client_order_created(order_id: int) -> None:
    await _post("/notify/client_order_created", {"order_id": order_id})


async def notify_pickup_reminder(order_id: int) -> None:
    await _post("/notify/pickup_reminder", {"order_id": order_id})


async def notify_return_reminder(order_id: int) -> None:
    await _post("/notify/return_reminder", {"order_id": order_id})


async def notify_status_changed(order_id: int) -> None:
    await _post("/notify/status_changed", {"order_id": order_id})
