import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.celery_app import celery_app
from src.clients.database.models.order import Order, OrderItem
from src.services.bot_notification import notify_pickup_reminder, notify_return_reminder

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = ("created", "in_progress", "taken")
_WINDOW_BEFORE = timedelta(hours=1, minutes=50)
_WINDOW_AFTER = timedelta(hours=2, minutes=10)


def _db_url() -> str:
    return (
        f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'db')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('DB_NAME')}"
    )


async def _send_pickup_reminders() -> None:
    engine = create_async_engine(_db_url())
    try:
        now = datetime.now(timezone.utc)
        window_start = now + _WINDOW_BEFORE
        window_end = now + _WINDOW_AFTER

        async with AsyncSession(engine) as session:
            min_start_subq = (
                select(OrderItem.order_id, func.min(OrderItem.rental_start).label("min_start"))
                .where(OrderItem.rental_start.isnot(None))
                .group_by(OrderItem.order_id)
                .subquery()
            )
            result = await session.execute(
                select(Order)
                .join(min_start_subq, Order.order_id == min_start_subq.c.order_id)
                .where(
                    min_start_subq.c.min_start >= window_start,
                    min_start_subq.c.min_start <= window_end,
                    Order.pickup_reminder_sent.is_(False),
                    Order.status.in_(_ACTIVE_STATUSES),
                )
            )
            orders = result.scalars().all()

            for order in orders:
                try:
                    await notify_pickup_reminder(order.order_id)
                    order.pickup_reminder_sent = True
                except Exception:
                    logger.exception("Failed to send pickup reminder for order %s", order.order_id)

            await session.commit()
    finally:
        await engine.dispose()


async def _send_return_reminders() -> None:
    engine = create_async_engine(_db_url())
    try:
        now = datetime.now(timezone.utc)
        window_start = now + _WINDOW_BEFORE
        window_end = now + _WINDOW_AFTER

        async with AsyncSession(engine) as session:
            max_end_subq = (
                select(OrderItem.order_id, func.max(OrderItem.rental_end).label("max_end"))
                .where(OrderItem.rental_end.isnot(None))
                .group_by(OrderItem.order_id)
                .subquery()
            )
            result = await session.execute(
                select(Order)
                .join(max_end_subq, Order.order_id == max_end_subq.c.order_id)
                .where(
                    max_end_subq.c.max_end >= window_start,
                    max_end_subq.c.max_end <= window_end,
                    Order.return_reminder_sent.is_(False),
                    Order.status.in_(_ACTIVE_STATUSES),
                )
            )
            orders = result.scalars().all()

            for order in orders:
                try:
                    await notify_return_reminder(order.order_id)
                    order.return_reminder_sent = True
                except Exception:
                    logger.exception("Failed to send return reminder for order %s", order.order_id)

            await session.commit()
    finally:
        await engine.dispose()


@celery_app.task(name="src.tasks.reminders.send_pickup_reminders")
def send_pickup_reminders() -> None:
    asyncio.run(_send_pickup_reminders())


@celery_app.task(name="src.tasks.reminders.send_return_reminders")
def send_return_reminders() -> None:
    asyncio.run(_send_return_reminders())
