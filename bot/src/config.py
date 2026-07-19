from os import getenv

import aiohttp
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv()


def _get_bot_token() -> str:
    token = getenv("API_TOKEN") or getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing bot token: set API_TOKEN or BOT_TOKEN")
    return token


def _get_backend_host() -> str:
    host = (getenv("BACKEND_HOST") or "").strip().rstrip("/")
    if not host:
        return "http://backend:8000"
    return host


API_TOKEN = _get_bot_token()
bot = Bot(API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

# Shared secret authorising the bot's server-to-server calls to the backend
# (and the backend's notifications to the bot). Must match INTERNAL_API_TOKEN
# on the backend.
INTERNAL_API_TOKEN = getenv("INTERNAL_API_TOKEN", "")
INTERNAL_HEADERS = {"X-Internal-Token": INTERNAL_API_TOKEN} if INTERNAL_API_TOKEN else {}

ADMIN_CHAT_ID = int(getenv("ADMIN_CHAT_ID") or 0)
PAYMENT_CARD_NUMBER = getenv("PAYMENT_CARD_NUMBER", "")
# Digits only (spaces stripped) — this is what clients see in a tappable <code>
# block, so it copies straight into a bank app's transfer field. Use this
# everywhere the card is shown; don't re-strip spaces at each call site.
CARD_NUMBER_PLAIN = PAYMENT_CARD_NUMBER.replace(" ", "")
DEPOSIT_AMOUNT = int(getenv("DEPOSIT_AMOUNT", 100000))

# Pickup point sent to the client (Telegram location pin) after a confirmed
# receipt. One source of truth so the coordinates aren't scattered as literals.
PICKUP_LATITUDE = 41.271367
PICKUP_LONGITUDE = 69.228406
FRONTEND_URL = (getenv("FRONTEND_URL") or "").strip().rstrip("/")
admin_calendar_url = f"{FRONTEND_URL}/app/admin" if FRONTEND_URL else ""
# DEPOSIT_PERCENT = int(getenv("DEPOSIT_PERCENT", 20))  # процент от суммы заказа


def fmt_price(amount: int | float) -> str:
    """Format price with space thousands separator: 2215000 → '2 215 000'"""
    return f"{int(amount):,}".replace(",", " ")

# API urls
host = _get_backend_host()
base_api_url = f"{host}/api/v1"
get_user_by_id_url = f"{base_api_url}/users/get_user_by_id"
create_user_url = f"{base_api_url}/users/create_user"
update_user_url = f"{base_api_url}/users/update_user"  # PATCH ?user_id=
get_admins_url = f"{base_api_url}/users/admins"
get_order_url = f"{base_api_url}/order"        # GET {get_order_url}/{order_id}
get_all_orders_url = f"{base_api_url}/order/"  # GET with optional ?user_id=
change_status_url = f"{base_api_url}/order/change_status"  # PATCH {change_status_url}/{order_id}?status=
