from datetime import date
from decimal import Decimal

from app.data.quality import inspect_fund_prices, inspect_stock_bars


def test_stock_quality_flags_invalid_ohlc_negative_volume_and_missing_day():
    rows = [
        {
            "trading_date": date(2026, 9, 14),
            "open": Decimal("100"),
            "high": Decimal("110"),
            "low": Decimal("99"),
            "close": Decimal("105"),
            "volume": Decimal("10"),
            "source_provider": "borsapy",
        },
        {
            "trading_date": date(2026, 9, 16),
            "open": Decimal("120"),
            "high": Decimal("110"),
            "low": Decimal("100"),
            "close": Decimal("115"),
            "volume": Decimal("-1"),
            "source_provider": "borsapy",
        },
    ]

    report = inspect_stock_bars(
        rows,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 16),
        extreme_return_threshold=Decimal("0.30"),
    )

    assert report.ok is False
    assert date(2026, 9, 15) in report.missing_business_dates
    assert date(2026, 9, 16) in report.invalid_ohlc
    assert date(2026, 9, 16) in report.negative_volume


def test_stock_quality_ignores_bist_full_closure():
    rows = [
        {
            "trading_date": date(2026, 4, 22),
            "open": Decimal("100"),
            "high": Decimal("110"),
            "low": Decimal("99"),
            "close": Decimal("105"),
            "volume": Decimal("10"),
            "source_provider": "borsapy",
        },
        {
            "trading_date": date(2026, 4, 24),
            "open": Decimal("106"),
            "high": Decimal("112"),
            "low": Decimal("104"),
            "close": Decimal("108"),
            "volume": Decimal("12"),
            "source_provider": "borsapy",
        },
    ]

    report = inspect_stock_bars(
        rows,
        start_date=date(2026, 4, 22),
        end_date=date(2026, 4, 24),
    )

    assert report.ok is True
    assert not report.missing_business_dates


def test_stock_quality_allows_single_source_and_normal_ohlc():
    rows = [
        {
            "trading_date": date(2026, 9, 14),
            "open": Decimal("100"),
            "high": Decimal("110"),
            "low": Decimal("99"),
            "close": Decimal("105"),
            "volume": Decimal("10"),
            "source_provider": "borsapy",
        },
        {
            "trading_date": date(2026, 9, 15),
            "open": Decimal("106"),
            "high": Decimal("112"),
            "low": Decimal("104"),
            "close": Decimal("108"),
            "volume": Decimal("12"),
            "source_provider": "borsapy",
        },
    ]

    report = inspect_stock_bars(
        rows,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 15),
    )

    assert report.ok is True
    assert not report.duplicate_keys
    assert not report.missing_business_dates
    assert not report.mixed_sources


def test_fund_quality_flags_duplicate_and_invalid_values():
    rows = [
        {
            "pricing_date": date(2026, 9, 14),
            "unit_price": Decimal("10"),
            "total_net_assets": Decimal("100"),
            "source_provider": "tefas",
        },
        {
            "pricing_date": date(2026, 9, 14),
            "unit_price": Decimal("0"),
            "total_net_assets": Decimal("-1"),
            "source_provider": "tefas",
        },
    ]

    report = inspect_fund_prices(
        rows,
        start_date=date(2026, 9, 14),
        end_date=date(2026, 9, 14),
    )

    assert report.ok is False
    assert report.duplicate_keys == (date(2026, 9, 14),)
    assert report.invalid_prices == (date(2026, 9, 14),)
    assert report.negative_assets == (date(2026, 9, 14),)
