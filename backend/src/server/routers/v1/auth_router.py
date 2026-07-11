from fastapi import APIRouter

# Phone-number auth (check/login/register) was removed: it let anyone log in as
# any user by knowing a phone number and allowed number enumeration. The Mini App
# authenticates via verified Telegram initData (see require_telegram_user); user
# creation happens server-to-server from the bot. This router is intentionally empty.
router = APIRouter(prefix="/auth", tags=["Auth"])
