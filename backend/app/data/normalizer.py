from datetime import datetime, timezone
from uuid import UUID

from app.schemas.market_data import FundDailyPriceCreate, StockDailyBarCreate

from .providers.base import ProviderFundPrice, ProviderStockBar


def normalize_stock_bar(
    record: ProviderStockBar,
    asset_id: UUID,
    provider: str,
    ingested_at: datetime | None = None,
) -> StockDailyBarCreate:
    timestamp = ingested_at or datetime.now(timezone.utc)
    return StockDailyBarCreate(
        asset_id=asset_id,
        trading_date=record.trading_date,
        open=record.open,
        high=record.high,
        low=record.low,
        close=record.close,
        adjusted_close=record.adjusted_close,
        volume=record.volume,
        turnover=record.turnover,
        source_provider=provider,
        source_timestamp=record.source_timestamp,
        ingested_at=timestamp,
    )


def normalize_fund_price(
    record: ProviderFundPrice,
    asset_id: UUID,
    provider: str,
    ingested_at: datetime | None = None,
) -> FundDailyPriceCreate:
    timestamp = ingested_at or datetime.now(timezone.utc)
    return FundDailyPriceCreate(
        asset_id=asset_id,
        pricing_date=record.pricing_date,
        unit_price=record.unit_price,
        total_net_assets=record.total_net_assets,
        source_provider=provider,
        source_timestamp=record.source_timestamp,
        ingested_at=timestamp,
    )
