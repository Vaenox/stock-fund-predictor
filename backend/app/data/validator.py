from datetime import date, datetime, timezone

from app.schemas.market_data import FundDailyPriceCreate, StockDailyBarCreate


class DataValidationError(ValueError):
    """Raised when provider data violates canonical data rules."""


def validate_stock_bar(record: StockDailyBarCreate, today: date | None = None) -> StockDailyBarCreate:
    current_date = today or datetime.now(timezone.utc).date()
    if record.trading_date > current_date:
        raise DataValidationError("stock trading_date cannot be in the future")
    return record


def validate_fund_price(record: FundDailyPriceCreate, today: date | None = None) -> FundDailyPriceCreate:
    current_date = today or datetime.now(timezone.utc).date()
    if record.pricing_date > current_date:
        raise DataValidationError("fund pricing_date cannot be in the future")
    return record


def validate_stock_bars(
    records: list[StockDailyBarCreate],
    today: date | None = None,
) -> list[StockDailyBarCreate]:
    seen: set[tuple[object, date]] = set()
    validated: list[StockDailyBarCreate] = []
    for record in records:
        key = (record.asset_id, record.trading_date)
        if key in seen:
            raise DataValidationError(
                f"duplicate canonical stock bar: asset_id={record.asset_id} date={record.trading_date}"
            )
        seen.add(key)
        validated.append(validate_stock_bar(record, today=today))
    return validated


def validate_fund_prices(
    records: list[FundDailyPriceCreate],
    today: date | None = None,
) -> list[FundDailyPriceCreate]:
    seen: set[tuple[object, date]] = set()
    validated: list[FundDailyPriceCreate] = []
    for record in records:
        key = (record.asset_id, record.pricing_date)
        if key in seen:
            raise DataValidationError(
                f"duplicate canonical fund price: asset_id={record.asset_id} date={record.pricing_date}"
            )
        seen.add(key)
        validated.append(validate_fund_price(record, today=today))
    return validated
