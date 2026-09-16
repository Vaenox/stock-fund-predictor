from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

from app.data.universe import sync_provider_universe
from app.data.providers.base import MarketDataProvider, ProviderSymbol
from app.models.market_data import AssetType


@dataclass
class FakeProvider(MarketDataProvider):
    symbols: list[ProviderSymbol]

    @property
    def name(self) -> str:
        return "fake"

    def list_symbols(self) -> list[ProviderSymbol]:
        return self.symbols

    def get_symbol_metadata(self, provider_symbol: str):
        raise NotImplementedError

    def get_daily_history(self, provider_symbol, start_date, end_date):
        raise NotImplementedError

    def get_latest_price(self, provider_symbol: str):
        raise NotImplementedError

    def get_fund_history(self, provider_symbol, start_date, end_date):
        raise NotImplementedError

    def health_check(self) -> bool:
        return True


class FakeScalarSession:
    def __init__(self):
        self.asset = None
        self.mapping = None
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement):
        text = str(statement).lower()
        if "assets" in text:
            return self.asset
        return self.mapping

    def add(self, obj):
        if hasattr(obj, "canonical_symbol"):
            self.asset = obj
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
        else:
            self.mapping = obj

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_sync_provider_universe_creates_assets_and_mappings():
    session = FakeScalarSession()
    provider = FakeProvider(
        [
            ProviderSymbol(
                provider="fake",
                provider_symbol="THYAO",
                canonical_symbol="thyao",
                name="Türk Hava Yolları",
                asset_type="STOCK",
            )
        ]
    )

    result = sync_provider_universe(session, provider, asset_type=AssetType.STOCK)

    assert result.discovered == 1
    assert result.assets_created == 1
    assert result.mappings_created == 1
    assert result.mappings_updated == 0
    assert session.committed is True
    assert session.rolled_back is False
