from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.data.normalizer import normalize_fund_price, normalize_stock_bar
from app.data.providers.base import ProviderFundPrice, ProviderStockBar
from app.data.validator import (
    DataValidationError,
    validate_fund_prices,
    validate_stock_bar,
    validate_stock_bars,
)


ASSET_ID = uuid4()


def stock_provider_record(trading_date: date = date(2026, 9, 14)) -> ProviderStockBar:
    return ProviderStockBar(
        provider_symbol="THYAO",
        trading_date=trading_date,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("99.00"),
        close=Decimal("104.00"),
        volume=Decimal("1000000"),
    )


def fund_provider_record(pricing_date: date = date(2026, 9, 14)) -> ProviderFundPrice:
    return ProviderFundPrice(
        provider_symbol="AAK",
        pricing_date=pricing_date,
        unit_price=Decimal("12.34567890"),
    )


def test_stock_normalizer_builds_canonical_record() -> None:
    ingested_at = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    result = normalize_stock_bar(stock_provider_record(), ASSET_ID, "matriks", ingested_at)

    assert result.asset_id == ASSET_ID
    assert result.source_provider == "matriks"
    assert result.close == Decimal("104.00")
    assert result.ingested_at == ingested_at


def test_fund_normalizer_builds_canonical_record() -> None:
    result = normalize_fund_price(fund_provider_record(), ASSET_ID, "tefas")

    assert result.asset_id == ASSET_ID
    assert result.source_provider == "tefas"
    assert result.unit_price == Decimal("12.34567890")


def test_stock_future_date_is_rejected() -> None:
    record = normalize_stock_bar(
        stock_provider_record(date(2026, 9, 16)),
        ASSET_ID,
        "matriks",
        datetime(2026, 9, 15, tzinfo=timezone.utc),
    )

    with pytest.raises(DataValidationError, match="future"):
        validate_stock_bar(record, today=date(2026, 9, 15))


def test_duplicate_stock_bars_are_rejected() -> None:
    first = normalize_stock_bar(stock_provider_record(), ASSET_ID, "matriks")
    second = normalize_stock_bar(stock_provider_record(), ASSET_ID, "matriks")

    with pytest.raises(DataValidationError, match="duplicate"):
        validate_stock_bars([first, second], today=date(2026, 9, 15))


def test_invalid_ohlc_is_rejected_by_schema() -> None:
    bad = stock_provider_record()
    bad = ProviderStockBar(
        provider_symbol=bad.provider_symbol,
        trading_date=bad.trading_date,
        open=bad.open,
        high=Decimal("98.00"),
        low=bad.low,
        close=bad.close,
    )

    with pytest.raises(ValueError, match="high"):
        normalize_stock_bar(bad, ASSET_ID, "matriks")


def test_duplicate_fund_prices_are_rejected() -> None:
    first = normalize_fund_price(fund_provider_record(), ASSET_ID, "tefas")
    second = normalize_fund_price(fund_provider_record(), ASSET_ID, "tefas")

    with pytest.raises(DataValidationError, match="duplicate"):
        validate_fund_prices([first, second], today=date(2026, 9, 15))
