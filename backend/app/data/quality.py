from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .calendar import expected_business_dates


@dataclass(frozen=True, slots=True)
class StockBarQualityReport:
    duplicate_keys: tuple[date, ...]
    invalid_ohlc: tuple[date, ...]
    negative_volume: tuple[date, ...]
    missing_business_dates: tuple[date, ...]
    extreme_return_dates: tuple[date, ...]
    mixed_sources: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not any((self.duplicate_keys, self.invalid_ohlc, self.negative_volume, self.mixed_sources))


@dataclass(frozen=True, slots=True)
class FundPriceQualityReport:
    duplicate_keys: tuple[date, ...]
    invalid_prices: tuple[date, ...]
    negative_assets: tuple[date, ...]
    missing_business_dates: tuple[date, ...]
    mixed_sources: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not any((self.duplicate_keys, self.invalid_prices, self.negative_assets, self.mixed_sources))


def inspect_stock_bars(
    rows: Iterable[dict],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    extreme_return_threshold: Decimal = Decimal("0.30"),
) -> StockBarQualityReport:
    rows = list(rows)
    seen: set[date] = set()
    duplicates: list[date] = []
    invalid_ohlc: list[date] = []
    negative_volume: list[date] = []
    extreme_returns: list[date] = []
    sources: set[str] = set()
    dates: set[date] = set()
    ordered = sorted(rows, key=lambda row: row["trading_date"])

    previous_close: Decimal | None = None
    for row in ordered:
        trading_date = row["trading_date"]
        dates.add(trading_date)
        if trading_date in seen:
            duplicates.append(trading_date)
        seen.add(trading_date)

        open_ = Decimal(str(row["open"]))
        high = Decimal(str(row["high"]))
        low = Decimal(str(row["low"]))
        close = Decimal(str(row["close"]))
        volume = row.get("volume")
        if not (low <= open_ <= high and low <= close <= high):
            invalid_ohlc.append(trading_date)
        if volume is not None and Decimal(str(volume)) < 0:
            negative_volume.append(trading_date)

        source = row.get("source_provider")
        if source:
            sources.add(str(source))

        if previous_close is not None and previous_close != 0:
            change = abs((close / previous_close) - Decimal("1"))
            if change > extreme_return_threshold:
                extreme_returns.append(trading_date)
        previous_close = close

    missing = (
        sorted(expected_business_dates(start_date, end_date) - dates)
        if start_date is not None and end_date is not None
        else []
    )

    return StockBarQualityReport(
        duplicate_keys=tuple(sorted(set(duplicates))),
        invalid_ohlc=tuple(sorted(set(invalid_ohlc))),
        negative_volume=tuple(sorted(set(negative_volume))),
        missing_business_dates=tuple(missing),
        extreme_return_dates=tuple(sorted(set(extreme_returns))),
        mixed_sources=tuple(sorted(sources)) if len(sources) > 1 else (),
    )


def inspect_fund_prices(
    rows: Iterable[dict],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> FundPriceQualityReport:
    rows = list(rows)
    seen: set[date] = set()
    duplicates: list[date] = []
    invalid_prices: list[date] = []
    negative_assets: list[date] = []
    sources: set[str] = set()
    dates: set[date] = set()

    for row in rows:
        pricing_date = row["pricing_date"]
        dates.add(pricing_date)
        if pricing_date in seen:
            duplicates.append(pricing_date)
        seen.add(pricing_date)

        if Decimal(str(row["unit_price"])) <= 0:
            invalid_prices.append(pricing_date)

        total_assets = row.get("total_net_assets")
        if total_assets is not None and Decimal(str(total_assets)) < 0:
            negative_assets.append(pricing_date)

        source = row.get("source_provider")
        if source:
            sources.add(str(source))

    missing = (
        sorted(expected_business_dates(start_date, end_date) - dates)
        if start_date is not None and end_date is not None
        else []
    )

    return FundPriceQualityReport(
        duplicate_keys=tuple(sorted(set(duplicates))),
        invalid_prices=tuple(sorted(set(invalid_prices))),
        negative_assets=tuple(sorted(set(negative_assets))),
        missing_business_dates=tuple(missing),
        mixed_sources=tuple(sorted(sources)) if len(sources) > 1 else (),
    )
