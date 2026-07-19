"""Fetch a client's chosen language for outbound bot messages.

Client notifications (order created, reminders, status changes) only have the
order/user_id at hand, so this looks up User.language_code over the internal
API. Falls back to Russian on any error — a translation lookup should never
block a notification.
"""

import logging
from http import HTTPStatus

import aiohttp

from src.config import INTERNAL_HEADERS, REQUEST_TIMEOUT, get_user_by_id_url
from src.i18n import DEFAULT_LANG, normalize_lang

logger = logging.getLogger(__name__)


async def fetch_user_language(user_id: int) -> str:
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                get_user_by_id_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    data = await resp.json()
                    return normalize_lang(data.get("language_code"))
    except Exception:
        logger.exception("Failed to fetch language for user_id=%s", user_id)
    return DEFAULT_LANG
