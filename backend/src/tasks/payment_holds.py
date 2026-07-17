import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
# Every mapped model must be imported before the first query in this process —
# SQLAlchemy configures all mappers together and Order's relationships reference
# sibling models (Basket, Product, ...) by string name (see migrations/env.py,
# which imports the same set for the same reason).
from src.clients.database.models.admin_user import AdminUser  # noqa: F401
from src.clients.database.models.basket import Basket, BasketItem  # noqa: F401
from src.clients.database.models.category import Category  # noqa: F401
from src.clients.database.models.order import Order, OrderItem  # noqa: F401
from src.clients.database.models.product import Product  # noqa: F401
from src.clients.database.models.promo import Promo  # noqa: F401
from src.clients.database.models.rental import ProductRental, ProductRentalSlot  # noqa: F401
from src.clients.database.models.user import User  # noqa: F401
from src.services.bot_notification import notify_hold_expired_cancelled
from src.services.errors import RentalUnavailableError
from src.services.order.schemas import OrderStatus
from src.services.rental.service import RentalService

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return (
        f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST', 'db')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('DB_NAME')}"
    )


async def _reconcile_expired_holds() -> None:
    """Cancel "created" orders whose 10-minute payment hold expired AND whose slot
    has since been genuinely taken by someone else. An expired-but-uncontested hold
    is left alone — still "created", still payable/approvable later — it simply no
    longer blocks availability (see RentalService._get_order_reservations).
    """
    engine = create_async_engine(_db_url())
    try:
        now = datetime.now(timezone.utc)
        # expire_on_commit=False: without it, committing one stale order's
        # cancellation would expire every other order object still queued in this
        # loop, and touching their (unawaited) attributes on the next iteration
        # raises MissingGreenlet instead of silently reloading.
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await session.execute(
                select(Order)
                .where(Order.status == OrderStatus.CREATED.value, Order.payment_deadline < now)
                .options(selectinload(Order.items))
            )
            stale_orders = result.unique().scalars().all()

            # ensure_product_available/available_quantity_for_window take an
            # explicit session and don't use self.session() — the factory here is
            # never invoked (same pattern as OrderService's use of RentalService).
            rental_service = RentalService(session=lambda: None)

            for order in stale_orders:
                demands: dict[tuple[int, datetime, datetime], int] = {}
                non_rental: list[tuple[int, int]] = []
                for item in order.items:
                    if item.rental_start is None:
                        non_rental.append((item.product_id, item.quantity))
                        continue
                    key = (item.product_id, item.rental_start, item.rental_end)
                    demands[key] = demands.get(key, 0) + item.quantity

                conflict = False
                try:
                    # exclude_order_id: an expired "created" order already excludes
                    # itself from _get_order_reservations (see the payment_deadline
                    # rule), but if a receipt races this sweep and confirms the same
                    # order right in between reading it here and checking it below,
                    # it would flip to in_progress and start counting against itself
                    # — defense in depth against that narrow window.
                    for product_id, quantity in non_rental:
                        await rental_service.ensure_product_available(
                            session=session,
                            product_id=product_id,
                            quantity=quantity,
                            rental_start=None,
                            rental_end=None,
                            exclude_order_id=order.order_id,
                        )
                    for (product_id, rental_start, rental_end), quantity in demands.items():
                        await rental_service.ensure_product_available(
                            session=session,
                            product_id=product_id,
                            quantity=quantity,
                            rental_start=rental_start,
                            rental_end=rental_end,
                            exclude_order_id=order.order_id,
                        )
                except RentalUnavailableError:
                    conflict = True

                if conflict:
                    # Capture before commit: expire_on_commit expires all attributes,
                    # and a plain (unawaited) attribute access on an expired async-ORM
                    # object raises MissingGreenlet instead of silently reloading.
                    stale_order_id = order.order_id
                    order.status = OrderStatus.CANCELED.value
                    await session.commit()
                    try:
                        await notify_hold_expired_cancelled(stale_order_id)
                    except Exception:
                        logger.exception(
                            "Failed to notify client about expired-hold cancellation for order %s", stale_order_id
                        )
                else:
                    await session.rollback()  # release the row locks ensure_product_available took
    finally:
        await engine.dispose()


@celery_app.task(name="src.tasks.payment_holds.reconcile_expired_holds")
def reconcile_expired_holds() -> None:
    asyncio.run(_reconcile_expired_holds())
