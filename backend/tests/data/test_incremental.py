from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app.data.incremental import ingest_fund_incremental, ingest_stock_incremental
from app.data.ingestion import IngestionResult
from app.data.providers.base import MarketDataProvider, ProviderFundPrice, ProviderStockBar, ProviderSymbol
from app.models.market_data import AssetType


class FakeProvider(MarketDataProvider):
    @property
    def name(self) -> str:
        return "fake"

    def list_symbols(self) -> list[ProviderSymbol]:
        return []

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        raise NotImplementedError

    def get_daily_history(self, provider_symbol, start_date, end_date):
        return [ProviderStockBar(provider_symbol, end_date, Decimal("1"), Decimal("2"), Decimal("1"), Decimal("2"))]

    def get_latest_price(self, provider_symbol):
        raise NotImplementedError

    def get_fund_history(self, provider_symbol, start_date, end_date):
        return [ProviderFundPrice(provider_symbol, end_date, Decimal("1.2"))]

    def health_check(self) -> bool:
        return True


class ScalarSession:
    def __init__(self, values):
        self.values = list(values)

    def scalar(self, _statement):
        return self.values.pop(0)


def _result(asset_id):
    return IngestionResult("fake", asset_id, date(2026, 9, 1), date(2026, 9, 15), 1, 1)


def test_stock_incremental_uses_bootstrap_when_empty():
    asset_id = uuid4()
    session = ScalarSession([None])
    with patch("app.data.incremental.ingest_stock_history", return_value=_result(asset_id)) as ingest:
        result = ingest_stock_incremental(
            session,
            FakeProvider(),
            asset_id=asset_id,
            provider_symbol="THYAO",
            as_of=date(2026, 9, 15),
            bootstrap_days=10,
            overlap_days=1,
        )

    assert result.bootstrap is True
    assert result.previous_last_date is None
    assert result.start_date == date(2026, 9, 6)
    assert result.end_date == date(2026, 9, 15)
    assert ingest.call_args.kwargs["start_date"] == date(2026, 9, 6)


def test_stock_incremental_replays_overlap_window():
    asset_id = uuid4()
    session = ScalarSession([date(2026, 9, 15)])
    with patch("app.data.incremental.ingest_stock_history", return_value=_result(asset_id)) as ingest:
        result = ingest_stock_incremental(
            session,
            FakeProvider(),
            asset_id=asset_id,
            provider_symbol="THYAO",
            as_of=date(2026, 9, 16),
            bootstrap_days=30,
            overlap_days=2,
        )

    assert result.bootstrap is False
    assert result.previous_last_date == date(2026, 9, 15)
    assert result.start_date == date(2026, 9, 13)
    assert result.end_date == date(2026, 9, 16)
    assert ingest.call_args.kwargs["start_date"] == date(2026, 9, 13)


def test_fund_incremental_uses_existing_last_date():
    asset_id = uuid4()
    session = ScalarSession([date(2026, 9, 10)])
    with patch("app.data.incremental.ingest_fund_history", return_value=_result(asset_id)) as ingest:
        result = ingest_fund_incremental(
            session,
            FakeProvider(),
            asset_id=asset_id,
            provider_symbol="AAA",
            as_of=date(2026, 9, 15),
            overlap_days=1,
        )

    assert result.start_date == date(2026, 9, 9)
    assert ingest.call_args.kwargs["end_date"] == date(2026, 9, 15)


def test_incremental_rejects_future_last_date():
    session = ScalarSession([date(2026, 9, 16)])
    try:
        ingest_stock_incremental(
            session,
            FakeProvider(),
            asset_id=uuid4(),
            provider_symbol="THYAO",
            as_of=date(2026, 9, 15),
        )
    except ValueError as exc:
        assert "after as_of" in str(exc)
    else:
        raise AssertionError("expected ValueError")
