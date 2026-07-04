from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from src.settings.billing import BillingSettings

# MUST stay in sync with the frontend mirror: frontend/src/utils/rental.ts.
# Reference cases live in backend/tests/test_rental_pricing.py.

_settings = BillingSettings()


def _to_local(value: datetime, tz: ZoneInfo) -> datetime:
    # Defensive: DB values are tz-aware UTC, but treat a naive datetime as UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz)


def get_billed_rental_half_days(
    rental_start: datetime | None,
    rental_end: datetime | None,
    settings: BillingSettings | None = None,
) -> int:
    """Billed duration in half-days (int, min = one full day).

    Evening pickup (>= evening_pickup_hour local) is free: billing starts the
    next day at day_start_hour. return_leniency_minutes are subtracted before
    rounding UP to the half-day step.
    """
    cfg = settings or _settings

    if rental_start is None or rental_end is None:
        return cfg.min_half_days

    tz = ZoneInfo(cfg.timezone)
    start_local = _to_local(rental_start, tz)
    end_local = _to_local(rental_end, tz)

    if start_local.hour >= cfg.evening_pickup_hour:
        next_day = (start_local + timedelta(days=1)).date()
        billing_start = datetime.combine(
            next_day, time(hour=cfg.day_start_hour), tzinfo=tz
        )
    else:
        billing_start = start_local

    billed_seconds = (
        int((end_local - billing_start).total_seconds())
        - cfg.return_leniency_minutes * 60
    )
    if billed_seconds <= 0:
        return cfg.min_half_days

    step_seconds = cfg.rounding_step_minutes * 60
    half_days = (billed_seconds + step_seconds - 1) // step_seconds  # ceil
    return max(cfg.min_half_days, half_days)


def get_billed_rental_days(
    rental_start: datetime | None,
    rental_end: datetime | None,
    settings: BillingSettings | None = None,
) -> float:
    """Billed days as a 0.5-step number, for display/API only."""
    return get_billed_rental_half_days(rental_start, rental_end, settings) / 2


def calculate_rental_line_half_day_units(
    unit_price: int,
    quantity: int,
    rental_start: datetime | None,
    rental_end: datetime | None,
    settings: BillingSettings | None = None,
) -> int:
    """Line amount in half-day units (sum × 2). Sum these across lines, then
    divide by 2 once, so odd-price half-day losses don't accumulate per line."""
    half_days = get_billed_rental_half_days(rental_start, rental_end, settings)
    return unit_price * quantity * half_days


def line_half_day_units(
    unit_price: int,
    quantity: int,
    rental_start: datetime | None,
    rental_end: datetime | None,
    price_mode: str = "per_day",
    settings: BillingSettings | None = None,
) -> int:
    """Line contribution in half-day units, honouring price_mode.

    - 'per_day': unit_price × qty × billed_half_days (charged per rental day).
    - 'flat':    unit_price × qty × 2 (charged once; ×2 so the shared //2 at the
      total level yields exactly unit_price × qty without multiplying by days).

    Summing units across all lines and dividing by 2 once keeps a single
    rounding point (see basket/order total calculators)."""
    if price_mode == "flat":
        return unit_price * quantity * 2
    return calculate_rental_line_half_day_units(
        unit_price, quantity, rental_start, rental_end, settings
    )


def calculate_rental_line_total(
    unit_price: int,
    quantity: int,
    rental_start: datetime | None,
    rental_end: datetime | None,
    settings: BillingSettings | None = None,
) -> int:
    """Per-line total in sum (display). Order/basket totals should sum
    half-day units instead and divide once."""
    units = calculate_rental_line_half_day_units(
        unit_price, quantity, rental_start, rental_end, settings
    )
    return units // 2


def floor_to_step(amount: int, step: int) -> int:
    if step <= 1:
        return amount
    return amount // step * step
