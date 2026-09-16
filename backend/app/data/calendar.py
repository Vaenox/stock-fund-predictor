from __future__ import annotations

from datetime import date, timedelta


# Borsa İstanbul Equity Market full-closure dates. Half-day sessions are
# intentionally excluded because a trading/pricing date still exists.
# Source: Borsa İstanbul official holiday schedules.
BIST_FULL_CLOSED_DATES: frozenset[date] = frozenset(
    {
        # 2025
        date(2025, 1, 1),
        date(2025, 3, 30),
        date(2025, 3, 31),
        date(2025, 4, 1),
        date(2025, 4, 23),
        date(2025, 5, 1),
        date(2025, 5, 19),
        date(2025, 6, 6),
        date(2025, 6, 7),
        date(2025, 6, 8),
        date(2025, 6, 9),
        date(2025, 7, 15),
        date(2025, 10, 29),
        # 2026
        date(2026, 1, 1),
        date(2026, 3, 20),
        date(2026, 4, 23),
        date(2026, 5, 1),
        date(2026, 5, 19),
        date(2026, 5, 27),
        date(2026, 5, 28),
        date(2026, 5, 29),
        date(2026, 7, 15),
        date(2026, 10, 29),
    }
)


def expected_business_dates(
    start_date: date,
    end_date: date,
    *,
    closed_dates: frozenset[date] = BIST_FULL_CLOSED_DATES,
) -> set[date]:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    current = start_date
    result: set[date] = set()
    while current <= end_date:
        if current.weekday() < 5 and current not in closed_dates:
            result.add(current)
        current += timedelta(days=1)
    return result
