"""Password hashing and admin-credential helpers.

Hashing uses PBKDF2-HMAC-SHA256 from the standard library so no extra crypto
dependency is needed. Stored format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.
"""

import hashlib
import hmac
import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database.models.admin_user import AdminUser

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$")
        if algorithm != _ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


def is_hashed(value: str) -> bool:
    return value.startswith(f"{_ALGORITHM}$")


async def authenticate_admin(session: AsyncSession, username: str, password: str) -> AdminUser | None:
    result = await session.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()
    if admin is None or not admin.is_active:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


async def admin_exists(session: AsyncSession, admin_id: int) -> bool:
    result = await session.execute(
        select(AdminUser.id).where(AdminUser.id == admin_id, AdminUser.is_active.is_(True))
    )
    return result.scalar_one_or_none() is not None


async def ensure_bootstrap_admin(session: AsyncSession, username: str, password: str) -> bool:
    """Create the initial admin from env credentials if the table is empty.

    Returns True if an admin was created. Does nothing once any admin exists, so
    changing the bootstrap password later has no effect — manage admins in the panel.
    """
    count = await session.scalar(select(func.count()).select_from(AdminUser))
    if count:
        return False
    session.add(AdminUser(username=username, password_hash=hash_password(password)))
    await session.commit()
    return True
