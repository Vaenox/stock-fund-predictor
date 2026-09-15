from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.market_data import (
    Asset,
    AssetProviderMapping,
    AssetType,
    FundDailyPrice,
    StockDailyBar,
)

from .normalizer import normalize_fund_price, normalize_stock_bar
from .providers.base import MarketDataProvider
from .validator import validate_fund_prices, validate_stock_bars


@dataclass(frozen=True, slots=True)
class IngestionResult:
    provider: str
    asset_id: UUID
    requested_start: date
    requested_end: date
    received: int
    written: int


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_asset(session: Session, asset_id: UUID, expected_type: AssetType) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.id == asset_id))
    if asset is None:
        raise ValueError(f"Asset not found: {asset_id}")
    if asset.asset_type != expected_type:
        raise ValueError(
            f"Asset {asset_id} has type {asset.asset_type}, expected {expected_type}"
        )
    return asset


def _require_mapping(
    session: Session,
    *,
    asset_id: UUID,
    provider: str,
    provider_symbol: str,
) -> None:
    mapping = session.scalar(
        select(AssetProviderMapping).where(
            AssetProviderMapping.asset_id == asset_id,
            AssetProviderMapping.provider == provider,
            AssetProviderMapping.provider_symbol == provider_symbol,
        )
    )
    if mapping is None:
        raise ValueError(
            "Provider mapping not found: "
            f"asset_id={asset_id}, provider={provider}, provider_symbol={provider_symbol}"
        )


def _execute_upsert(session: Session, stmt) -> None:
    try:
        session.execute(stmt)
        session.commit()
    except Exception:
        session.rollback()
        raise


def ingest_stock_history(
    session: Session,
    provider: MarketDataProvider,
    *,
    asset_id: UUID,
    provider_symbol: str,
    start_date: date,
    end_date: date,
    today: date | None = None,
) -> IngestionResult:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    _require_asset(session, asset_id, AssetType.STOCK)
    _require_mapping(
        session,
        asset_id=asset_id,
        provider=provider.name,
        provider_symbol=provider_symbol,
    )

    raw_records = provider.get_daily_history(provider_symbol, start_date, end_date)
    ingested_at = _utc_now()
    normalized = [
        normalize_stock_bar(record, asset_id, provider.name, ingested_at=ingested_at)
        for record in raw_records
    ]
    validated = validate_stock_bars(normalized, today=today)

    if not validated:
        return IngestionResult(
            provider=provider.name,
            asset_id=asset_id,
            requested_start=start_date,
            requested_end=end_date,
            received=0,
            written=0,
        )

    rows = [record.model_dump() for record in validated]
    stmt = insert(StockDailyBar).values(rows)
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=[StockDailyBar.asset_id, StockDailyBar.trading_date],
        set_={
            "open": excluded.open,
            "high": excluded.high,
            "low": excluded.low,
            "close": excluded.close,
            "adjusted_close": excluded.adjusted_close,
            "volume": excluded.volume,
            "turnover": excluded.turnover,
            "source_provider": excluded.source_provider,
            "source_timestamp": excluded.source_timestamp,
            "ingested_at": excluded.ingested_at,
        },
    )
    _execute_upsert(session, stmt)

    return IngestionResult(
        provider=provider.name,
        asset_id=asset_id,
        requested_start=start_date,
        requested_end=end_date,
        received=len(raw_records),
        written=len(validated),
    )


def ingest_fund_history(
    session: Session,
    provider: MarketDataProvider,
    *,
    asset_id: UUID,
    provider_symbol: str,
    start_date: date,
    end_date: date,
    today: date | None = None,
) -> IngestionResult:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    _require_asset(session, asset_id, AssetType.FUND)
    _require_mapping(
        session,
        asset_id=asset_id,
        provider=provider.name,
        provider_symbol=provider_symbol,
    )

    raw_records = provider.get_fund_history(provider_symbol, start_date, end_date)
    ingested_at = _utc_now()
    normalized = [
        normalize_fund_price(record, asset_id, provider.name, ingested_at=ingested_at)
        for record in raw_records
    ]
    validated = validate_fund_prices(normalized, today=today)

    if not validated:
        return IngestionResult(
            provider=provider.name,
            asset_id=asset_id,
            requested_start=start_date,
            requested_end=end_date,
            received=0,
            written=0,
        )

    rows = [record.model_dump() for record in validated]
    stmt = insert(FundDailyPrice).values(rows)
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=[FundDailyPrice.asset_id, FundDailyPrice.pricing_date],
        set_={
            "unit_price": excluded.unit_price,
            "total_net_assets": excluded.total_net_assets,
            "source_provider": excluded.source_provider,
            "source_timestamp": excluded.source_timestamp,
            "ingested_at": excluded.ingested_at,
        },
    )
    _execute_upsert(session, stmt)

    return IngestionResult(
        provider=provider.name,
        asset_id=asset_id,
        requested_start=start_date,
        requested_end=end_date,
        received=len(raw_records),
        written=len(validated),
    )
