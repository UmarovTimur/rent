from os import getenv

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

# API urls
host = _get_backend_host()
base_api_url = f"{host}/api/v1"
get_user_by_id_url = f"{base_api_url}/users/get_user_by_id"
create_user_url = f"{base_api_url}/users/create_user"
