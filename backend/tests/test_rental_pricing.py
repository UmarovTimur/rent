"""Reference suite for the half-day billing algorithm.

The parametrized table below is the owner's approved reference and is mirrored
verbatim in frontend/src/utils/rental.test.ts — keep both in sync.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.services.rental_pricing import (
    calculate_rental_line_half_day_units,
    calculate_rental_line_total,
    floor_to_step,
    get_billed_rental_days,
    get_billed_rental_half_days,
)

TASHKENT = ZoneInfo("Asia/Tashkent")


def local(y: int, m: int, d: int, hh: int, mm: int = 0) -> datetime:
    """Tashkent-local wall time → UTC, the way production data arrives."""
    return datetime(y, m, d, hh, mm, tzinfo=TASHKENT).astimezone(timezone.utc)


# 2026-07-10 is a Friday.
FRI, SAT, SUN, MON = 10, 11, 12, 13


# ─── Owner's reference table ─────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("start", "end", "expected_half_days"),
    [
        # Fri 19:00 → Sun 19:00: billing starts Sat 09:00, 34h−2 = 32h → 1.5 days
        (local(2026, 7, FRI, 19), local(2026, 7, SUN, 19), 3),
        # Fri 19:00 → Sat 20:00: starts Sat 09:00, 11h−2 = 9h → minimum 1 day
        (local(2026, 7, FRI, 19), local(2026, 7, SAT, 20), 2),
        # Sat 09:00 → Sun 10:30: 25.5h−2 = 23.5h → 1 day
        (local(2026, 7, SAT, 9), local(2026, 7, SUN, 10, 30), 2),
        # Sat 09:00 → Sun 18:00: 33h−2 = 31h → 1.5 days
        (local(2026, 7, SAT, 9), local(2026, 7, SUN, 18), 3),
        # "Week-long trip": starts Tue 09:00, 150h−2 = 148h → 6.5 days.
        # (Owner's row said "Mon 18:00 → Sun 15:00" but computed 150h, which
        # is Tue 09:00 → Mon 15:00 — the hours are the normative part.)
        (local(2026, 7, MON, 18), local(2026, 7, 20, 15), 13),
        # The literal Mon 18:00 → Sun 15:00 dates: Tue 09:00 → Sun 15:00
        # = 126h − 2 = 124h → 5.5 days
        (local(2026, 7, MON, 18), local(2026, 7, 19, 15), 11),
    ],
)
def test_owner_reference_table(start, end, expected_half_days):
    assert get_billed_rental_half_days(start, end) == expected_half_days


# ─── Grace boundary ──────────────────────────────────────────────────────────
def test_pickup_exactly_1700_triggers_grace():
    # 17:00 → billing from next day 09:00; Sat 17:00 → Sun 17:00 = 8h−2 → min 1 day
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 17), local(2026, 7, SUN, 17)
    ) == 2


def test_pickup_1659_no_grace():
    # 16:59 → billing from actual time; 24h+1min − 2h = 22h1m → 1 day
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 16, 59), local(2026, 7, SUN, 17)
    ) == 2
    # …but a longer window shows the difference: Sat 16:59 → Sun 23:59
    # = 31h − 2h = 29h → ceil(29/12) = 3 (1.5 days), while a 17:00 pickup
    # of the same return bills from Sun 09:00 = 15h − 2h = 13h → 2 (1 day)
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 16, 59), local(2026, 7, SUN, 23, 59)
    ) == 3
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 17), local(2026, 7, SUN, 23, 59)
    ) == 2


# ─── Rounding boundary: exactly 24h + 2h leniency ────────────────────────────
def test_exactly_26h_is_one_day():
    # Sat 09:00 → Sun 11:00 = 26h − 2h = 24h → exactly 2 half-days → 1 day
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 9), local(2026, 7, SUN, 11)
    ) == 2


def test_26h_plus_one_minute_is_one_and_half():
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 9), local(2026, 7, SUN, 11, 1)
    ) == 3


# ─── Degenerate windows → minimum ────────────────────────────────────────────
def test_return_before_billing_start():
    # Fri 19:00 → Fri 20:00: billing would start Sat 09:00, negative duration
    assert get_billed_rental_half_days(
        local(2026, 7, FRI, 19), local(2026, 7, FRI, 20)
    ) == 2


def test_return_equals_billing_start():
    assert get_billed_rental_half_days(
        local(2026, 7, FRI, 19), local(2026, 7, SAT, 9)
    ) == 2


def test_duration_swallowed_by_leniency():
    # 1.5h rental − 2h leniency ≤ 0 → minimum
    assert get_billed_rental_half_days(
        local(2026, 7, SAT, 9), local(2026, 7, SAT, 10, 30)
    ) == 2


def test_none_dates_return_minimum():
    assert get_billed_rental_half_days(None, None) == 2
    assert get_billed_rental_half_days(local(2026, 7, SAT, 9), None) == 2
    assert get_billed_rental_half_days(None, local(2026, 7, SAT, 9)) == 2


def test_naive_datetime_treated_as_utc():
    aware_start = local(2026, 7, SAT, 9)
    aware_end = local(2026, 7, SUN, 18)
    naive_start = aware_start.replace(tzinfo=None)
    naive_end = aware_end.replace(tzinfo=None)
    assert get_billed_rental_half_days(naive_start, naive_end) == \
        get_billed_rental_half_days(aware_start, aware_end)


# ─── Display days ────────────────────────────────────────────────────────────
def test_get_billed_rental_days_fractional():
    assert get_billed_rental_days(
        local(2026, 7, FRI, 19), local(2026, 7, SUN, 19)
    ) == 1.5
    assert get_billed_rental_days(
        local(2026, 7, MON, 18), local(2026, 7, 20, 15)
    ) == 6.5


# ─── Money math ──────────────────────────────────────────────────────────────
def test_line_total_one_and_half_days():
    # 150 000 × 1 × 1.5 = 225 000
    assert calculate_rental_line_total(
        150_000, 1, local(2026, 7, FRI, 19), local(2026, 7, SUN, 19)
    ) == 225_000


def test_line_units_and_odd_price_division():
    start, end = local(2026, 7, FRI, 19), local(2026, 7, SUN, 19)  # 3 half-days
    assert calculate_rental_line_half_day_units(333, 1, start, end) == 999
    assert calculate_rental_line_total(333, 1, start, end) == 499  # 999 // 2

    # Order-total path: units summed first, divided once, floored once.
    units = (
        calculate_rental_line_half_day_units(333, 1, start, end)
        + calculate_rental_line_half_day_units(15_000, 2, start, end)
    )
    assert units == 999 + 90_000
    assert floor_to_step(units // 2, 100) == 45_400  # 45499 → 45400


def test_floor_to_step():
    assert floor_to_step(22_551, 100) == 22_500
    assert floor_to_step(22_500, 100) == 22_500
    assert floor_to_step(99, 100) == 0
    assert floor_to_step(22_551, 1) == 22_551
