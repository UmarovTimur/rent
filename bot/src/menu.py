"""Persistent Telegram reply-keyboard ("main menu") shown at the bottom of the
chat in place of the on-screen keyboard — the primary way clients and admins
navigate the bot, replacing slash commands (which stay working as a fallback).

Inline keyboards (order action buttons, filters, pagination, language picker)
stay inline: they're tied to a specific message/record and can't live on a
persistent bottom button.

Admin-facing labels stay Russian (matches the existing i18n.py policy — the
admin panel is Russian-only); the client-facing language button goes through t().
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from src.i18n import t

MENU_ORDERS = "📋 Заказы"
MENU_CALENDAR = "📅 Календарь"
MENU_SEND = "✉️ Написать клиенту"
MENU_BAN = "🚫 Бан/Разбан"

# Shared across every guided-dialog flow (send message, ban toggle, ...) so
# there's one label to match on instead of a copy per module.
CANCEL_LABEL = "❌ Отмена"


def build_main_menu(*, is_admin: bool, lang: str, admin_calendar_url: str = "") -> ReplyKeyboardMarkup:
    language_button = KeyboardButton(text=t("menu_language", lang))

    if not is_admin:
        my_orders_button = KeyboardButton(text=t("menu_my_orders", lang))
        return ReplyKeyboardMarkup(
            keyboard=[[my_orders_button], [language_button]], resize_keyboard=True
        )

    # One tap straight into the Mini App calendar when configured — no need for
    # the intermediate inline button the /admin_calendar command still sends.
    calendar_button = (
        KeyboardButton(text=MENU_CALENDAR, web_app=WebAppInfo(url=admin_calendar_url))
        if admin_calendar_url
        else KeyboardButton(text=MENU_CALENDAR)
    )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_ORDERS), calendar_button],
            [KeyboardButton(text=MENU_SEND), KeyboardButton(text=MENU_BAN)],
            [language_button],
        ],
        resize_keyboard=True,
    )
