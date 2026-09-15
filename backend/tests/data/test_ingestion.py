from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.data.ingestion import ingest_fund_history, ingest_stock_history
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

    def get_daily_history(self, provider_symbol: str, start_date: date, end_date: date) -> list[ProviderStockBar]:
        return [
            ProviderStockBar(
                provider_symbol=provider_symbol,
                trading_date=date(2026, 9, 10),
                open=Decimal("100"),
                high=Decimal("105"),
                low=Decimal("99"),
                close=Decimal("104"),
            )
        ]

    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        raise NotImplementedError

    def get_fund_history(self, provider_symbol: str, start_date: date, end_date: date) -> list[ProviderFundPrice]:
        return [
            ProviderFundPrice(
                provider_symbol=provider_symbol,
                pricing_date=date(2026, 9, 10),
                unit_price=Decimal("12.3456"),
            )
        ]

    def health_check(self) -> bool:
        return True


class FakeSession:
    def __init__(self, asset_type: AssetType):
        self.asset = SimpleNamespace(id=uuid4(), asset_type=asset_type)
        self.executed = None
        self.committed = False

    def scalar(self, _statement):
        return self.asset

    def execute(self, statement):
        self.executed = statement
        return None

    def commit(self):
        self.committed = True


def test_ingest_stock_history_normalizes_validates_and_commits():
    session = FakeSession(AssetType.STOCK)
    result = ingest_stock_history(
        session,
        FakeProvider(),
        asset_id=session.asset.id,
        provider_symbol="THYAO",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 15),
        today=date(2026, 9, 15),
    )

    assert result.received == 1
    assert result.written == 1
    assert session.committed is True
    assert session.executed is not None


def test_ingest_fund_history_normalizes_validates_and_commits():
    session = FakeSession(AssetType.FUND)
    result = ingest_fund_history(
        session,
        FakeProvider(),
        asset_id=session.asset.id,
        provider_symbol="AAA",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 15),
        today=date(2026, 9, 15),
    )

    assert result.received == 1
    assert result.written == 1
    assert session.committed is True
    assert session.executed is not None


def test_ingest_rejects_wrong_asset_type():
    session = FakeSession(AssetType.FUND)

    try:
        ingest_stock_history(
            session,
            FakeProvider(),
            asset_id=session.asset.id,
            provider_symbol="THYAO",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 15),
            today=date(2026, 9, 15),
        )
    except ValueError as exc:
        assert "expected" in str(exc)
    else:
        raise AssertionError("expected ValueError")
