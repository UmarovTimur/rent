from __future__ import annotations

from datetime import datetime

_DAY_MICROSECONDS = 24 * 60 * 60 * 1_000_000


def get_billed_rental_days(
    rental_start: datetime | None,
    rental_end: datetime | None,
) -> int:
    if rental_start is None or rental_end is None:
        return 1

    duration = rental_end - rental_start
    duration_microseconds = (
        duration.days * _DAY_MICROSECONDS
        + duration.seconds * 1_000_000
        + duration.microseconds
    )

    if duration_microseconds <= 0:
        return 1

    whole_days, remainder = divmod(duration_microseconds, _DAY_MICROSECONDS)

    # Round to nearest day, but keep exact .5 day ties on the lower integer.
    rounded_days = whole_days + (1 if remainder * 2 > _DAY_MICROSECONDS else 0)
    return max(1, int(rounded_days))


def calculate_rental_line_total(
    unit_price: int,
    quantity: int,
    rental_start: datetime | None,
    rental_end: datetime | None,
) -> int:
    billed_days = get_billed_rental_days(rental_start, rental_end)
    return unit_price * quantity * billed_days
