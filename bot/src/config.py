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

ADMIN_CHAT_ID = int(getenv("ADMIN_CHAT_ID") or 0)
PAYMENT_CARD_NUMBER = getenv("PAYMENT_CARD_NUMBER", "")
DEPOSIT_AMOUNT = int(getenv("DEPOSIT_AMOUNT", 50000))
# DEPOSIT_PERCENT = int(getenv("DEPOSIT_PERCENT", 20))  # процент от суммы заказа


def fmt_price(amount: int | float) -> str:
    """Format price with space thousands separator: 2215000 → '2 215 000'"""
    return f"{int(amount):,}".replace(",", " ")

# API urls
host = _get_backend_host()
base_api_url = f"{host}/api/v1"
get_user_by_id_url = f"{base_api_url}/users/get_user_by_id"
create_user_url = f"{base_api_url}/users/create_user"
get_admins_url = f"{base_api_url}/users/admins"
get_order_url = f"{base_api_url}/order"        # GET {get_order_url}/{order_id}
get_all_orders_url = f"{base_api_url}/order/"  # GET with optional ?user_id=
change_status_url = f"{base_api_url}/order/change_status"  # PATCH {change_status_url}/{order_id}?status=
