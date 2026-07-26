import asyncio
import html
import logging
from http import HTTPStatus

import aiohttp
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.config import (
    ADMIN_CHAT_ID,
    INTERNAL_HEADERS,
    MANAGER_USERNAME,
    PICKUP_ADDRESS,
    REQUEST_TIMEOUT,
    admin_calendar_url,
    bot,
    change_status_url,
    fmt_price,
    get_admins_url,
    get_all_orders_url,
    get_order_url,
    get_user_by_id_url,
    update_user_url,
)
from src.i18n import t
from src.menu import CANCEL_LABEL, MENU_BAN, MENU_CALENDAR, MENU_ORDERS, build_main_menu
from src.order_items import format_order_items
from src.user_lang import fetch_user_language

router = Router(name="admin_callbacks")
logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {"created", "in_progress", "taken"}
_PAGE_SIZE = 5

_STATUS_LABEL = {
    "created": "🆕 Создан",
    "in_progress": "▶️ В работе",
    "taken": "📦 Отдано клиенту",
    "paused": "⏸ Пауза",
    "returned": "✅ Возвращён",
    "completed": "🚫 Закрыт (неуспешно)",
    "canceled": "❌ Отменён",
}


# ─── Admin check ─────────────────────────────────────────────────────────────

async def _is_admin(user_id: int) -> bool:
    if ADMIN_CHAT_ID and user_id == ADMIN_CHAT_ID:
        return True
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                get_user_by_id_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
            ) as resp:
                if resp.status == HTTPStatus.OK:
                    data = await resp.json()
                    return bool(data.get("is_admin"))
    except Exception:
        logger.exception("Admin check failed for user_id=%s", user_id)
    return False


# ─── Keyboards ───────────────────────────────────────────────────────────────

# Order filters AND pagination live on the persistent bottom reply-keyboard
# (not inline) so navigating orders happens in Telegram's keyboard UI, not via
# buttons stuck under a chat message. Per-order action buttons (approve/pause/…)
# stay inline — those are tied to one specific order card.
MENU_BACK_TO_MAIN = "🔙 Главное меню"
NAV_PREV = "⬅️ Назад"
NAV_NEXT = "Вперёд ➡️"
SEARCH_BY_NUMBER = "🔍 Поиск по номеру"

FILTER_LABEL_TO_KEY = {
    "🆕 Создан": "created",
    "▶️ В работе": "in_progress",
    "📦 Отдано": "taken",
    "⏸ Пауза": "paused",
    "✅ Возвращён": "returned",
    "🚫 Закрыт": "completed",
    "❌ Отменён": "canceled",
    "🔥 Активные": "active",
    "📋 Все": "all",
}

_FILTER_ROWS = [
    ["🆕 Создан", "▶️ В работе", "📦 Отдано"],
    ["⏸ Пауза", "✅ Возвращён", "🚫 Закрыт"],
    ["❌ Отменён", "🔥 Активные", "📋 Все"],
]


def _orders_reply_keyboard(page: int | None = None, total_pages: int = 1) -> ReplyKeyboardMarkup:
    """Bottom keyboard for the orders screen: a conditional prev/next nav row
    (only while viewing a multi-page result), search-by-number, the status
    filters, and back-to-main.
    """
    rows: list[list[str]] = []
    if page is not None and total_pages > 1:
        nav = []
        if page > 0:
            nav.append(NAV_PREV)
        if page < total_pages - 1:
            nav.append(NAV_NEXT)
        if nav:
            rows.append(nav)
    rows.append([SEARCH_BY_NUMBER])
    rows.extend(_FILTER_ROWS)
    rows.append([MENU_BACK_TO_MAIN])
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=label) for label in row] for row in rows],
        resize_keyboard=True,
    )


def _order_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status == "created":
        # Only a brand-new order can be approved.
        builder.button(text="✅ Одобрить", callback_data=f"order:approve:{order_id}")
        builder.button(text="⏸ Пауза",    callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
        builder.adjust(3)
    elif status == "in_progress":
        # Approved and holding the slot — next physical step is handing the gear over.
        builder.button(text="📦 Отдал",   callback_data=f"order:handover:{order_id}")
        builder.button(text="⏸ Пауза",    callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть", callback_data=f"order:close:{order_id}")
        builder.adjust(3)
    elif status == "taken":
        # Gear is with the client — next physical step is getting it back.
        # "Отменить отдал" covers marking it as taken by mistake.
        builder.button(text="✅ Вернули",       callback_data=f"order:return:{order_id}")
        builder.button(text="↩️ Отменить отдал", callback_data=f"order:undo_handover:{order_id}")
        builder.button(text="⏸ Пауза",          callback_data=f"order:pause:{order_id}")
        builder.button(text="🔒 Закрыть",       callback_data=f"order:close:{order_id}")
        builder.adjust(2, 2)
    elif status == "paused":
        builder.button(text="▶️ Возобновить", callback_data=f"order:approve:{order_id}")
        builder.button(text="🔒 Закрыть",     callback_data=f"order:close:{order_id}")
        builder.adjust(2)
    elif status == "returned":
        # Undo goes back to "taken" (a return always follows a handover) — not
        # a full reopen, so admins correcting a mis-click keep the handover marker.
        builder.button(text="↩️ Отменить возврат", callback_data=f"order:undo_return:{order_id}")
        builder.adjust(1)
    elif status == "completed":
        builder.button(text="↩️ Открыть заново", callback_data=f"order:reopen:{order_id}")
        builder.adjust(1)
    return builder.as_markup()


# ─── Message formatter ───────────────────────────────────────────────────────

def _format_order(order: dict) -> str:
    # Client-controlled fields (name/phone/address/comment/product names) MUST
    # be HTML-escaped: the bot sends with parse_mode=HTML, so a raw "<" or a
    # crafted tag would make Telegram reject the whole message — silently
    # dropping the admin notification (the order would bypass the queue).
    lines = [
        f"<b>Заказ #{order['order_id']}</b>",
        f"📅 {order['order_date'][:16].replace('T', ' ')}",
    ]
    if order.get("first_name"):
        lines.append(f"👤 {html.escape(str(order['first_name']))}")
    if order.get("phone"):
        lines.append(f"📞 {html.escape(str(order['phone']))}")
    lines.append(f"📍 {PICKUP_ADDRESS}")

    payment = "карта" if order.get("payment_option") == "card" else "наличные"
    lines.append(f"💳 Оплата: {payment}")
    lines.append(f"💰 Итого: {fmt_price(order['total_price'])} сум")

    items = order.get("items", [])
    # One overall pickup/return window for the whole order — repeating it per
    # line (every item shares the same trip dates) just added noise.
    rental_starts = [i["rental_start"] for i in items if i.get("rental_start")]
    rental_ends = [i["rental_end"] for i in items if i.get("rental_end")]
    if rental_starts and rental_ends:
        start = min(rental_starts)[:16].replace("T", " ")
        end = max(rental_ends)[:16].replace("T", " ")
        lines.append(f"📆 {start} — {end}")

    if order.get("comment"):
        lines.append(f"💬 {html.escape(str(order['comment']))}")

    if items:
        lines.append("")
        lines.append("📦 <b>Состав:</b>")
        lines.append(format_order_items(items))

    status_label = _STATUS_LABEL.get(order.get("status", ""), order.get("status", ""))
    lines.append(f"\nСтатус: {status_label}")
    return "\n".join(lines)


# ─── Notification sender (called from server.py and message_handlers.py) ─────

# Every (chat_id, message_id) currently showing a given order's card, across
# every admin — so approving/pausing/closing from any one admin refreshes
# every other admin's copy too, not just the one who tapped. Populated
# whenever a card is sent (new-order push, receipt-approval push, /orders
# browsing); never explicitly pruned (bounded by order volume, acceptable for
# a long-running process).
_ORDER_CARD_LOCATIONS: dict[int, list[tuple[int, int]]] = {}


def _register_order_card(order_id: int, chat_id: int, message_id: int) -> None:
    _ORDER_CARD_LOCATIONS.setdefault(order_id, []).append((chat_id, message_id))


async def get_admin_recipients() -> list[int]:
    """Every admin chat id that should see order notifications: everyone
    flagged is_admin, plus the legacy ADMIN_CHAT_ID fallback (deduplicated) —
    so all admins are equally in the loop regardless of which one (if any) is
    configured as the "default" chat.
    """
    recipients: list[int] = []
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(get_admins_url, headers=INTERNAL_HEADERS) as resp:
                if resp.status == HTTPStatus.OK:
                    recipients = list(await resp.json())
                else:
                    logger.warning("Could not fetch admin list: %s", resp.status)
    except Exception:
        logger.exception("Failed to fetch admin list")
    if ADMIN_CHAT_ID and ADMIN_CHAT_ID not in recipients:
        recipients.append(ADMIN_CHAT_ID)
    return recipients


async def send_order_to_admins(order_id: int) -> None:
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
                if resp.status != HTTPStatus.OK:
                    logger.warning("Could not fetch order %s for notification: %s", order_id, resp.status)
                    return
                order = await resp.json()

        recipients = await get_admin_recipients()
        text = _format_order(order)
        keyboard = _order_keyboard(order_id, order["status"])

        for admin_id in recipients:
            try:
                sent = await bot.send_message(admin_id, text, reply_markup=keyboard)
                _register_order_card(order_id, admin_id, sent.message_id)
            except Exception:
                logger.exception("Failed to send order notification to admin %s", admin_id)
    except Exception:
        logger.exception("send_order_to_admins failed for order_id=%s", order_id)


# ─── Order action callback ────────────────────────────────────────────────────

_ACTION_STATUS = {
    "approve":       "in_progress",
    "pause":         "paused",
    "close":         "completed",
    "reopen":        "in_progress",
    "handover":      "taken",       # "Отдал" — gear physically given to the client
    "return":        "returned",    # "Вернули" — gear physically given back, successful outcome
    "undo_handover": "in_progress", # mistake correction: undo "Отдал"
    "undo_return":   "taken",       # mistake correction: undo "Вернули"
}

# Only reachable from this status — guards against a stale/double-tapped
# keyboard applying an action out of order (e.g. two admins, or a leftover
# card from before a pause/reopen).
_ACTION_REQUIRES_STATUS = {
    "handover": "in_progress",
    "return": "taken",
    "undo_handover": "taken",
    "undo_return": "returned",
    "reopen": "completed",
}

# Actions where the admin is asked for a short comment explaining the change to
# the client, before it's applied. "approve" only prompts when it means resuming
# a paused order — the very first confirmation (from "created") keeps its own
# automatic "your order is confirmed" message with no prompt. "handover"/"return"
# are physical-handoff markers the client already knows about — no prompt needed.
_ACTION_VERB = {
    "pause": "приостановили",
    "close": "закрыли",
    "approve": "возобновили",
}


class OrderAction(StatesGroup):
    waiting_comment = State()


class AdminMenu(StatesGroup):
    # Active while the admin is browsing the orders screen — the bottom
    # reply-keyboard shows status filters + pagination instead of the main menu.
    orders_filter = State()
    # Active after tapping "🔍 Поиск по номеру" — waiting for the order number.
    waiting_order_number = State()


async def _apply_order_action(
    order_id: int,
    action: str,
    *,
    client_text_key: str | None,
    comment: str | None,
    reply_chat_id: int,
    admin_message_id: int | None,
) -> None:
    """Patch the order's status, notify the client (if client_text_key is given,
    translated to the client's language, with the admin's comment appended), and
    refresh every admin's copy of the card in place — not just the one who
    tapped, so no other admin is left looking at a stale button.
    """
    new_status = _ACTION_STATUS[action]

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.patch(
            f"{change_status_url}/{order_id}",
            params={"status": new_status},
            headers=INTERNAL_HEADERS,
        ) as resp:
            if resp.status == HTTPStatus.CONFLICT:
                # Another admin's action landed first (the backend re-checks the
                # transition under a row lock — see RentalService.update_rental_status)
                # — tell this admin plainly instead of a bare error, and refresh
                # their card with what's actually true now.
                await _handle_stale_action(order_id, reply_chat_id, admin_message_id)
                return
            if resp.status not in {HTTPStatus.NO_CONTENT, HTTPStatus.OK}:
                await bot.send_message(reply_chat_id, f"❌ Ошибка при смене статуса заказа #{order_id}.")
                return

        async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
            if resp.status != HTTPStatus.OK:
                await bot.send_message(reply_chat_id, "Статус обновлён.")
                return
            order = await resp.json()

    if client_text_key:
        lang = await fetch_user_language(order["user_id"])
        text = t(client_text_key, lang, order_id=order_id)
        if comment:
            text += f"\n\n💬 {comment}"
        try:
            await bot.send_message(order["user_id"], text)
        except Exception:
            logger.exception("Failed to notify client %s about order %s (%s)", order.get("user_id"), order_id, action)

    if action == "handover":
        # Mirrors backend's BONUS_ACCRUAL_RATE (rental/service.py) — bonus
        # coins are credited server-side on this same transition (entering
        # "taken"); this just tells the client what landed in their balance.
        bonus = int(order["total_price"] * 0.10)
        if bonus > 0:
            lang = await fetch_user_language(order["user_id"])
            try:
                await bot.send_message(order["user_id"], t("coins_earned", lang, amount=fmt_price(bonus)))
            except Exception:
                logger.exception("Failed to notify client %s about bonus for order %s", order.get("user_id"), order_id)

    await _refresh_all_admin_cards(
        order_id, order, new_status, fallback_chat_id=reply_chat_id, fallback_message_id=admin_message_id
    )


async def _refresh_admin_card(
    order_id: int, order: dict, new_status: str, chat_id: int, message_id: int
) -> None:
    """Update one admin card in place after a status change.

    The card may be a plain text message (from send_order_to_admins) or a photo
    message with a caption (the receipt forwarded by _process_receipt) — Telegram
    rejects edit_message_text on a photo message ("there is no text to edit"), so
    try text first and fall back to caption, then to reply-markup-only as a last
    resort, instead of silently leaving a stale keyboard on the card.
    """
    text = _format_order(order)
    keyboard = _order_keyboard(order_id, new_status)
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
        return
    except Exception:
        pass
    try:
        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, reply_markup=keyboard)
        return
    except Exception:
        pass
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    except Exception:
        logger.exception("Failed to refresh admin card for order %s", order_id)


async def _refresh_all_admin_cards(
    order_id: int,
    order: dict,
    new_status: str,
    *,
    fallback_chat_id: int,
    fallback_message_id: int | None,
) -> None:
    locations = set(_ORDER_CARD_LOCATIONS.get(order_id, []))
    if fallback_message_id is not None:
        locations.add((fallback_chat_id, fallback_message_id))
    if not locations:
        return
    for chat_id, message_id in locations:
        await _refresh_admin_card(order_id, order, new_status, chat_id, message_id)
    _ORDER_CARD_LOCATIONS[order_id] = list(locations)


async def _handle_stale_action(order_id: int, chat_id: int, message_id: int | None) -> None:
    """Another admin's tap already changed this order's status — fetch the
    current state, tell this admin, and refresh every admin's card with it
    (their own included, if we know where it is).
    """
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
                if resp.status != HTTPStatus.OK:
                    await bot.send_message(chat_id, f"❌ Заказ #{order_id} уже изменил другой админ.")
                    return
                order = await resp.json()
    except Exception:
        logger.exception("Failed to refresh stale card for order %s", order_id)
        await bot.send_message(chat_id, f"❌ Заказ #{order_id} уже изменил другой админ.")
        return

    await bot.send_message(chat_id, f"ℹ️ Заказ #{order_id} уже обновил другой админ — обновляю карточку.")
    await _refresh_all_admin_cards(
        order_id, order, order["status"], fallback_chat_id=chat_id, fallback_message_id=message_id
    )


@router.callback_query(F.data.startswith("order:"))
async def handle_order_action(callback: CallbackQuery, state: FSMContext) -> None:
    # Authorization: order cards live in the admin chat, but a non-admin member
    # of that chat could otherwise tap these buttons and drive any order's
    # state. Every admin action must re-verify the tapper server-side.
    if not callback.from_user or not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверный формат", show_alert=True)
        return

    _, action, order_id_str = parts
    if action not in _ACTION_STATUS:
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    order_id = int(order_id_str)

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
            current_status = None
            if resp.status == HTTPStatus.OK:
                current = await resp.json()
                current_status = current.get("status")

    # Guard against double-approval (fast double-tap / two admins): only a
    # "created" or "paused" order can be approved/resumed.
    if action == "approve" and current_status not in {"created", "paused"}:
        await callback.answer("Заказ уже одобрен", show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_order_keyboard(order_id, current_status or "")
            )
        return

    # Guard against a stale keyboard: "Отдал" only makes sense from in_progress,
    # "Вернули" only from taken (can't return gear that was never handed over).
    required_status = _ACTION_REQUIRES_STATUS.get(action)
    if required_status and current_status != required_status:
        await callback.answer("Статус заказа уже изменился", show_alert=True)
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_order_keyboard(order_id, current_status or "")
            )
        return

    if not callback.message:
        return

    is_resume = action == "approve" and current_status == "paused"
    # Pause/close/resume are all "tell the client why" moments — prompt for a
    # short comment before applying. The very first confirmation (approve from
    # "created") keeps its existing automatic message and isn't prompted.
    if action in {"pause", "close"} or is_resume:
        await state.update_data(
            pending_order_id=order_id,
            pending_action=action,
            pending_chat_id=callback.message.chat.id,
            pending_message_id=callback.message.message_id,
        )
        await state.set_state(OrderAction.waiting_comment)
        await callback.answer()
        await bot.send_message(
            callback.message.chat.id,
            f"Напишите комментарий для клиента — почему заказ #{order_id} {_ACTION_VERB[action]} "
            f"(когда открыть снова и т.п.). Или отправьте «-», чтобы отправить без комментария.",
        )
        return

    direct_client_text_key = {
        "approve": "order_approved",
        "return": "order_returned",
    }.get(action)

    await _apply_order_action(
        order_id,
        action,
        client_text_key=direct_client_text_key,
        comment=None,
        reply_chat_id=callback.message.chat.id,
        admin_message_id=callback.message.message_id,
    )
    await callback.answer()


@router.message(OrderAction.waiting_comment, F.text)
async def handle_order_action_comment(message: Message, state: FSMContext) -> None:
    # This state is only ever entered from the admin-gated handle_order_action,
    # so a non-admin can't reach it — but re-verify anyway (defense in depth).
    if not message.from_user or not await _is_admin(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    order_id = data.get("pending_order_id")
    action = data.get("pending_action")
    admin_chat_id = data.get("pending_chat_id")
    admin_message_id = data.get("pending_message_id")
    await state.clear()

    if not order_id or not action:
        return

    comment = (message.text or "").strip()
    if comment == "-":
        comment = None

    client_text_key = {
        "pause": "order_paused_client",
        "close": "order_closed_client",
        "approve": "order_resumed_client",
    }.get(action)

    await _apply_order_action(
        order_id,
        action,
        client_text_key=client_text_key,
        comment=comment,
        reply_chat_id=admin_chat_id or message.chat.id,
        admin_message_id=admin_message_id,
    )
    await message.answer(f"Готово: заказ #{order_id} обновлён.")


# ─── Filter callback ─────────────────────────────────────────────────────────

def _pluralize_orders(n: int) -> str:
    if 11 <= n % 100 <= 19:
        return f"{n} заказов"
    r = n % 10
    if r == 1:
        return f"{n} заказ"
    if 2 <= r <= 4:
        return f"{n} заказа"
    return f"{n} заказов"


# Message ids (summary + order cards) of the currently displayed page, keyed by
# the admin's chat id — so paginating/searching can delete the previous page
# before rendering the next, instead of piling up messages forever.
_LAST_PAGE_MSG_IDS: dict[int, list[int]] = {}


async def _clear_last_page(chat_id: int) -> None:
    for message_id in _LAST_PAGE_MSG_IDS.pop(chat_id, []):
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass


async def _render_orders_page(message: Message, state: FSMContext, status_filter: str, page: int) -> None:
    """Render a filtered/paginated orders page. Navigation (prev/next/filter/
    search) is driven from the bottom reply-keyboard, so this always sends fresh
    messages and remembers the current filter/page in FSM for the nav buttons.
    Per-order action buttons stay inline (tied to a specific order card).
    """
    chat_id = message.chat.id

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(get_all_orders_url, headers=INTERNAL_HEADERS) as resp:
            if resp.status != HTTPStatus.OK:
                await message.answer("❌ Не удалось получить заказы.")
                return
            all_orders: list[dict] = await resp.json()

    if status_filter == "all":
        filtered = all_orders
        label = "Все заказы"
    elif status_filter == "active":
        filtered = [o for o in all_orders if o.get("status") in _ACTIVE_STATUSES]
        label = "Активные"
    else:
        filtered = [o for o in all_orders if o.get("status") == status_filter]
        label = _STATUS_LABEL.get(status_filter, status_filter)

    filtered.sort(key=lambda o: o.get("order_date", ""), reverse=True)
    total = len(filtered)
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    shown = filtered[page * _PAGE_SIZE : page * _PAGE_SIZE + _PAGE_SIZE]

    await state.update_data(orders_filter=status_filter, orders_page=page)
    await _clear_last_page(chat_id)

    keyboard = _orders_reply_keyboard(page, total_pages)
    if not shown:
        sent = await message.answer(f"📋 {label}: заказов нет.", reply_markup=keyboard)
        _LAST_PAGE_MSG_IDS[chat_id] = [sent.message_id]
        return

    page_line = f" — стр. {page + 1}/{total_pages}" if total_pages > 1 else ""
    summary = await message.answer(
        f"📋 {label}: {_pluralize_orders(total)}{page_line}", reply_markup=keyboard
    )
    msg_ids = [summary.message_id]
    for order in shown:
        text = _format_order(order)
        sent = await message.answer(text, reply_markup=_order_keyboard(order["order_id"], order["status"]))
        msg_ids.append(sent.message_id)
        _register_order_card(order["order_id"], chat_id, sent.message_id)
        await asyncio.sleep(0.05)
    _LAST_PAGE_MSG_IDS[chat_id] = msg_ids


# ─── /orders command ─────────────────────────────────────────────────────────

async def _send_filter_menu(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not await _is_admin(user_id):
        await message.answer(
            "Эта команда доступна только администраторам.",
            reply_markup=build_main_menu(is_admin=False, lang="ru", admin_calendar_url=admin_calendar_url),
        )
        return
    await state.set_state(AdminMenu.orders_filter)
    await message.answer("📋 Выберите фильтр заказов:", reply_markup=_orders_reply_keyboard())


@router.message(Command("orders"))
async def orders_menu(message: Message, state: FSMContext) -> None:
    await _send_filter_menu(message, state)


@router.message(F.text == MENU_ORDERS, StateFilter(None))
async def menu_orders_button(message: Message, state: FSMContext) -> None:
    await _send_filter_menu(message, state)


@router.message(F.text == MENU_BACK_TO_MAIN)
async def admin_menu_back_to_main(message: Message, state: FSMContext) -> None:
    # Deliberately NOT gated on AdminMenu.orders_filter: a "go home" control
    # must always work, regardless of whatever state the admin happens to be
    # in (e.g. if a new-order push or some other update landed in between and
    # left the FSM state out of sync with what the admin expects).
    if not message.from_user or not await _is_admin(message.from_user.id):
        return
    await state.clear()
    await _clear_last_page(message.chat.id)
    await message.answer(
        t("menu_refreshed", "ru"),
        reply_markup=build_main_menu(is_admin=True, lang="ru", admin_calendar_url=admin_calendar_url),
    )


@router.message(AdminMenu.orders_filter, F.text.in_(FILTER_LABEL_TO_KEY.keys()))
async def admin_menu_filter_select(message: Message, state: FSMContext) -> None:
    status_filter = FILTER_LABEL_TO_KEY[message.text]
    await _render_orders_page(message, state, status_filter, page=0)


@router.message(AdminMenu.orders_filter, F.text.in_({NAV_PREV, NAV_NEXT}))
async def admin_menu_paginate(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    status_filter = data.get("orders_filter", "all")
    page = data.get("orders_page", 0)
    page = page - 1 if message.text == NAV_PREV else page + 1
    await _render_orders_page(message, state, status_filter, max(0, page))


@router.message(AdminMenu.orders_filter, F.text == SEARCH_BY_NUMBER)
async def admin_menu_search_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminMenu.waiting_order_number)
    await message.answer(
        "Введите номер заказа (например 42):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=CANCEL_LABEL)]], resize_keyboard=True
        ),
    )


@router.message(AdminMenu.waiting_order_number, F.text == CANCEL_LABEL)
async def admin_menu_search_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminMenu.orders_filter)
    await message.answer("📋 Выберите фильтр заказов:", reply_markup=_orders_reply_keyboard())


@router.message(AdminMenu.waiting_order_number, F.text)
async def admin_menu_search_number(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().lstrip("#")
    if not raw.isdigit():
        await message.answer("Номер заказа — это число. Попробуйте ещё раз или нажмите «❌ Отмена».")
        return

    order_id = int(raw)
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(f"{get_order_url}/{order_id}", headers=INTERNAL_HEADERS) as resp:
                order = await resp.json() if resp.status == HTTPStatus.OK else None
    except Exception:
        logger.exception("Order search fetch failed for #%s", order_id)
        order = None

    await state.set_state(AdminMenu.orders_filter)
    if not order:
        await message.answer(
            f"Заказ #{order_id} не найден.", reply_markup=_orders_reply_keyboard()
        )
        return

    await _clear_last_page(message.chat.id)
    sent = await message.answer(
        _format_order(order),
        reply_markup=_order_keyboard(order["order_id"], order["status"]),
    )
    _register_order_card(order["order_id"], message.chat.id, sent.message_id)
    _LAST_PAGE_MSG_IDS[message.chat.id] = [sent.message_id]
    await message.answer("📋 Фильтр / поиск:", reply_markup=_orders_reply_keyboard())


# ─── /admin_calendar command ──────────────────────────────────────────────────

async def _send_admin_calendar(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    if not await _is_admin(user_id):
        await message.answer(
            "Эта команда доступна только администраторам.",
            reply_markup=build_main_menu(is_admin=False, lang="ru", admin_calendar_url=admin_calendar_url),
        )
        return
    if not admin_calendar_url:
        await message.answer("Календарь не настроен: не задан FRONTEND_URL.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Открыть календарь аренды", web_app=WebAppInfo(url=admin_calendar_url))
    await message.answer("Календарь аренды:", reply_markup=builder.as_markup())


@router.message(Command("admin_calendar"))
async def admin_calendar(message: Message) -> None:
    await _send_admin_calendar(message)


# Only reached if MENU_CALENDAR fell back to a plain text button (no
# admin_calendar_url configured) — with a URL the button opens the Mini App
# directly and never sends a text message to the bot.
@router.message(F.text == MENU_CALENDAR, StateFilter(None))
async def menu_calendar_button(message: Message) -> None:
    await _send_admin_calendar(message)


# ─── Ban / unban a user ───────────────────────────────────────────────────────

class BanUser(StatesGroup):
    waiting_target = State()


async def _resolve_user_id(target_raw: str) -> tuple[int | None, str]:
    """Resolve @username or a numeric id to a Telegram user id.

    Returns (user_id, label) — user_id is None if it couldn't be resolved
    (label then holds a human-readable reason).
    """
    target_raw = target_raw.strip()
    if target_raw.lstrip("-").isdigit():
        return int(target_raw), target_raw

    username = target_raw if target_raw.startswith("@") else f"@{target_raw}"
    try:
        chat = await bot.get_chat(username)
        return chat.id, username
    except Exception:
        return None, (
            "Не удалось найти пользователя по username — пришлите его user_id "
            "(например, взяв его из карточки заказа)."
        )


@router.message(F.text == MENU_BAN, StateFilter(None))
async def menu_ban_start(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    if not await _is_admin(message.from_user.id):
        await message.answer(
            "Эта команда доступна только администраторам.",
            reply_markup=build_main_menu(is_admin=False, lang="ru", admin_calendar_url=admin_calendar_url),
        )
        return

    await state.set_state(BanUser.waiting_target)
    await message.answer(
        "Кого забанить или разбанить? Пришлите @username или user_id.\n"
        "Повторное нажатие для того же пользователя снимает бан.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=CANCEL_LABEL)]], resize_keyboard=True),
    )


@router.message(BanUser.waiting_target, F.text == CANCEL_LABEL)
async def menu_ban_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Отменено.",
        reply_markup=build_main_menu(is_admin=True, lang="ru", admin_calendar_url=admin_calendar_url),
    )


@router.message(BanUser.waiting_target, F.text)
async def menu_ban_target(message: Message, state: FSMContext) -> None:
    await state.clear()
    target_raw = (message.text or "").strip()

    user_id, label = await _resolve_user_id(target_raw)
    reply_markup = build_main_menu(is_admin=True, lang="ru", admin_calendar_url=admin_calendar_url)
    if user_id is None:
        await message.answer(label, reply_markup=reply_markup)
        return

    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        async with session.get(
            get_user_by_id_url, params={"user_id": user_id}, headers=INTERNAL_HEADERS
        ) as resp:
            if resp.status != HTTPStatus.OK:
                await message.answer(f"Пользователь {label} не найден в базе.", reply_markup=reply_markup)
                return
            user = await resp.json()

        was_banned = bool(user.get("is_banned"))
        new_banned = not was_banned
        async with session.patch(
            update_user_url,
            params={"user_id": user_id},
            json={"is_banned": new_banned},
            headers=INTERNAL_HEADERS,
        ) as resp:
            if resp.status != HTTPStatus.OK:
                await message.answer(f"Не удалось изменить статус {label}.", reply_markup=reply_markup)
                return

    display = f"@{user['username']}" if user.get("username") else label
    status_text = "🚫 забанен" if new_banned else "✅ разбанен"
    await message.answer(f"Пользователь {display} теперь {status_text}.", reply_markup=reply_markup)

    # Notify the user in the bot at the moment of blocking (with the manager
    # contact) — the Mini App only shows a short "blocked" label, the actionable
    # "contact the manager" text is pushed here instead.
    if new_banned:
        lang = await fetch_user_language(user_id)
        try:
            await bot.send_message(user_id, t("banned_notice", lang, manager=MANAGER_USERNAME))
        except Exception:
            logger.exception("Failed to notify banned user %s", user_id)
