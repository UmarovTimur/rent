"""Brute-force throttle for admin login.

Both admin login paths (the JSON /api/admin/login endpoint and the SQLAdmin
form) funnel their credential check through here so failed attempts are counted
in Redis (already in the stack — RedisSettings) and locked out after a
threshold. Fail-open: if Redis is unreachable the check never blocks a
legitimate admin, it only loses the throttle for that request.
"""

import logging

import redis.asyncio as aioredis

from src.settings.redis import RedisSettings

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 7          # allowed failures per key before lockout
_WINDOW_SECONDS = 15 * 60  # lockout / counting window

_redis: aioredis.Redis | None = None


def _client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = RedisSettings()
        _redis = aioredis.from_url(settings.url, decode_responses=True)
    return _redis


def _key(identifier: str) -> str:
    return f"admin_login_fail:{identifier}"


async def is_locked_out(*identifiers: str) -> bool:
    """True if any of the identifiers (e.g. username, client IP) is over the
    failure threshold within the window."""
    try:
        client = _client()
        for ident in identifiers:
            if not ident:
                continue
            count = await client.get(_key(ident))
            if count is not None and int(count) >= _MAX_ATTEMPTS:
                return True
    except Exception:
        logger.exception("Login rate-limit check failed (allowing through)")
    return False


async def register_failure(*identifiers: str) -> None:
    try:
        client = _client()
        for ident in identifiers:
            if not ident:
                continue
            key = _key(ident)
            new_count = await client.incr(key)
            if new_count == 1:
                await client.expire(key, _WINDOW_SECONDS)
    except Exception:
        logger.exception("Login rate-limit increment failed")


async def reset(*identifiers: str) -> None:
    try:
        client = _client()
        for ident in identifiers:
            if ident:
                await client.delete(_key(ident))
    except Exception:
        logger.exception("Login rate-limit reset failed")
