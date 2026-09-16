from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.market_data import FundDailyPrice, StockDailyBar

from .ingestion import IngestionResult, ingest_fund_history, ingest_stock_history
from .providers.base import MarketDataProvider


@dataclass(frozen=True, slots=True)
class IncrementalIngestionResult:
    ingestion: IngestionResult
    previous_last_date: date | None
    start_date: date
    end_date: date
    overlap_days: int
    bootstrap: bool


def _window(
    last_date: date | None,
    *,
    as_of: date,
    bootstrap_days: int,
    overlap_days: int,
) -> tuple[date, bool]:
    if bootstrap_days < 1:
        raise ValueError("bootstrap_days must be positive")
    if overlap_days < 0:
        raise ValueError("overlap_days cannot be negative")
    if last_date is not None and last_date > as_of:
        raise ValueError("last persisted date cannot be after as_of")

    if last_date is None:
        return as_of - timedelta(days=bootstrap_days - 1), True

    start = max(last_date - timedelta(days=overlap_days), date.min)
    return start, False


def _last_stock_date(session: Session, asset_id: UUID) -> date | None:
    return session.scalar(
        select(func.max(StockDailyBar.trading_date)).where(
            StockDailyBar.asset_id == asset_id
        )
    )


def _last_fund_date(session: Session, asset_id: UUID) -> date | None:
    return session.scalar(
        select(func.max(FundDailyPrice.pricing_date)).where(
            FundDailyPrice.asset_id == asset_id
        )
    )


def ingest_stock_incremental(
    session: Session,
    provider: MarketDataProvider,
    *,
    asset_id: UUID,
    provider_symbol: str,
    as_of: date | None = None,
    bootstrap_days: int = 30,
    overlap_days: int = 1,
) -> IncrementalIngestionResult:
    end_date = as_of or date.today()
    previous_last_date = _last_stock_date(session, asset_id)
    start_date, bootstrap = _window(
        previous_last_date,
        as_of=end_date,
        bootstrap_days=bootstrap_days,
        overlap_days=overlap_days,
    )
    result = ingest_stock_history(
        session,
        provider,
        asset_id=asset_id,
        provider_symbol=provider_symbol,
        start_date=start_date,
        end_date=end_date,
        today=end_date,
    )
    return IncrementalIngestionResult(
        ingestion=result,
        previous_last_date=previous_last_date,
        start_date=start_date,
        end_date=end_date,
        overlap_days=overlap_days,
        bootstrap=bootstrap,
    )


def ingest_fund_incremental(
    session: Session,
    provider: MarketDataProvider,
    *,
    asset_id: UUID,
    provider_symbol: str,
    as_of: date | None = None,
    bootstrap_days: int = 30,
    overlap_days: int = 1,
) -> IncrementalIngestionResult:
    end_date = as_of or date.today()
    previous_last_date = _last_fund_date(session, asset_id)
    start_date, bootstrap = _window(
        previous_last_date,
        as_of=end_date,
        bootstrap_days=bootstrap_days,
        overlap_days=overlap_days,
    )
    result = ingest_fund_history(
        session,
        provider,
        asset_id=asset_id,
        provider_symbol=provider_symbol,
        start_date=start_date,
        end_date=end_date,
        today=end_date,
    )
    return IncrementalIngestionResult(
        ingestion=result,
        previous_last_date=previous_last_date,
        start_date=start_date,
        end_date=end_date,
        overlap_days=overlap_days,
        bootstrap=bootstrap,
    )
