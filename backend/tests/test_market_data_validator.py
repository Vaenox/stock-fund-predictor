from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.market_data import FundDailyPriceCreate, StockDailyBarCreate
from app.data.validator import (
    DataValidationError,
    validate_fund_prices,
    validate_stock_bar,
    validate_stock_bars,
)


ASSET_ID = uuid4()
INGESTED_AT = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def stock_bar(trading_date: date) -> StockDailyBarCreate:
    return StockDailyBarCreate(
        asset_id=ASSET_ID,
        trading_date=trading_date,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        source_provider="matriks",
        ingested_at=INGESTED_AT,
    )


def fund_price(pricing_date: date) -> FundDailyPriceCreate:
    return FundDailyPriceCreate(
        asset_id=ASSET_ID,
        pricing_date=pricing_date,
        unit_price=Decimal("12.345678"),
        source_provider="tefas",
        ingested_at=INGESTED_AT,
    )


def test_future_stock_date_is_rejected() -> None:
    with pytest.raises(DataValidationError, match="cannot be in the future"):
        validate_stock_bar(stock_bar(date(2026, 9, 16)), today=date(2026, 9, 15))


def test_duplicate_stock_dates_are_rejected() -> None:
    record = stock_bar(date(2026, 9, 15))
    with pytest.raises(DataValidationError, match="duplicate canonical stock bar"):
        validate_stock_bars([record, record], today=date(2026, 9, 15))


def test_duplicate_fund_dates_are_rejected() -> None:
    record = fund_price(date(2026, 9, 15))
    with pytest.raises(DataValidationError, match="duplicate canonical fund price"):
        validate_fund_prices([record, record], today=date(2026, 9, 15))


def test_validation_accepts_valid_stock_bar() -> None:
    record = stock_bar(date(2026, 9, 15))
    assert validate_stock_bar(record, today=date(2026, 9, 15)) is record
