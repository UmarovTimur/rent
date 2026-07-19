"""Best-effort sync of confirmed orders into a shared Google Calendar.

Mirrors the resilience style of bot_notification.py: every external call is
wrapped so a Google API hiccup only gets logged, never breaks the order flow
that triggered it. No-ops entirely (feature off) if GOOGLE_CALENDAR_* isn't
configured — see settings/google_calendar.py.

Only confirmed orders (in_progress/taken) get a calendar event; a 10-minute
payment hold ("created") is deliberately not synced, so unpaid holds never
clutter the calendar. The event title is prefixed with the current status
("[Отдано]", "[Пауза]", "[Возвращён]", "[Закрыт]") and colored per status
(see _STATUS_COLOR_ID) so admins can tell them apart at a glance without
opening each event; cancelled orders have theirs deleted instead.
"""

import asyncio
import json
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.clients.database.models.order import Order, OrderItem
from src.container import container
from src.settings.google_calendar import GoogleCalendarSettings

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_TIMEZONE = "Asia/Tashkent"

# Google Calendar's fixed event color palette (colorId 1-11) — picked semantically:
# https://developers.google.com/calendar/api/v3/reference/colors/get
_STATUS_COLOR_ID = {
    "in_progress": "9",   # Blueberry — confirmed, holding the slot
    "taken": "6",         # Tangerine — handed over to the client
    "paused": "3",        # Grape — on hold
    "returned": "10",     # Basil (green) — successful outcome
    "completed": "11",    # Tomato (red) — closed unsuccessfully
}

_service = None  # module-level cache — built once, reused across calls


def _get_service(settings: GoogleCalendarSettings):
    global _service
    if _service is None:
        info = json.loads(settings.service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
        _service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    return _service


def _order_event_body(order: Order) -> dict | None:
    """None when the order has no dated rental items — nothing to put on a calendar."""
    rental_items = [item for item in order.items if item.rental_start is not None and item.rental_end is not None]
    if not rental_items:
        return None

    start = min(item.rental_start for item in rental_items)
    end = max(item.rental_end for item in rental_items)

    lines = [
        f"  • {(item.product.name if item.product else f'Товар #{item.product_id}')} × {item.quantity}"
        for item in order.items
    ]
    description_parts = [f"Клиент: {order.first_name or '—'}"]
    if order.phone:
        description_parts.append(f"Телефон: {order.phone}")
    description_parts.append(f"Сумма: {order.total_price:,} сум".replace(",", " "))
    if order.comment:
        description_parts.append(f"Комментарий: {order.comment}")
    description_parts.append("")
    description_parts.append("Состав:")
    description_parts.extend(lines)

    return {
        "summary": f"Заказ #{order.order_id} — {order.first_name or order.phone or '—'}",
        "description": "\n".join(description_parts),
        # rental_start/end are tz-aware UTC instants already; timeZone here only
        # controls how Google *displays* them (Tashkent local time), not the instant.
        "start": {"dateTime": start.isoformat(), "timeZone": _TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": _TIMEZONE},
    }


async def sync_order_calendar(order_id: int) -> None:
    settings = GoogleCalendarSettings()
    if not settings.id or not settings.service_account_json:
        return  # feature not configured — silent no-op

    db = container.database()
    async with db.session() as session:
        result = await session.execute(
            select(Order)
            .where(Order.order_id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
        )
        order = result.unique().scalar_one_or_none()
        if not order:
            return

        try:
            await _sync(settings, session, order)
        except Exception:
            logger.exception("Google Calendar sync failed for order %s", order_id)


async def _sync(settings: GoogleCalendarSettings, session: AsyncSession, order: Order) -> None:
    service = _get_service(settings)
    calendar_id = settings.id

    if order.status in {"in_progress", "taken"}:
        body = _order_event_body(order)
        if body is None:
            return
        if order.status == "taken":
            body["summary"] = f"[Отдано] {body['summary']}"
        body["colorId"] = _STATUS_COLOR_ID[order.status]
        if order.google_event_id:
            event_id = order.google_event_id
            await asyncio.to_thread(
                lambda: service.events()
                .patch(calendarId=calendar_id, eventId=event_id, body=body)
                .execute()
            )
        else:
            created = await asyncio.to_thread(
                lambda: service.events().insert(calendarId=calendar_id, body=body).execute()
            )
            order.google_event_id = created["id"]
            await session.commit()

    elif order.status in {"paused", "completed", "returned"} and order.google_event_id:
        body = _order_event_body(order)
        if body is None:
            return
        prefix = {
            "paused": "[Пауза] ",
            "completed": "[Закрыт] ",     # unsuccessful outcome — no return, no revenue
            "returned": "[Возвращён] ",   # successful outcome — client returned the gear
        }[order.status]
        body["summary"] = f"{prefix}{body['summary']}"
        body["colorId"] = _STATUS_COLOR_ID[order.status]
        event_id = order.google_event_id
        await asyncio.to_thread(
            lambda: service.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=body)
            .execute()
        )

    elif order.status == "canceled" and order.google_event_id:
        event_id = order.google_event_id
        await asyncio.to_thread(
            lambda: service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        )
        order.google_event_id = None
        await session.commit()

    # "created" (unconfirmed payment hold) — never synced, nothing to do.
