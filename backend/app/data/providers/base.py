from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderSymbol:
    provider: str
    provider_symbol: str
    canonical_symbol: str
    name: str
    asset_type: str
    isin: str | None = None
    exchange: str | None = None
    currency: str = "TRY"


@dataclass(frozen=True, slots=True)
class ProviderStockBar:
    provider_symbol: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None = None
    volume: Decimal | None = None
    turnover: Decimal | None = None
    source_timestamp: datetime | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ProviderFundPrice:
    provider_symbol: str
    pricing_date: date
    unit_price: Decimal
    total_net_assets: Decimal | None = None
    source_timestamp: datetime | None = None
    raw: dict[str, Any] | None = None


class MarketDataProvider(ABC):
    """Provider contract; adapters only translate provider-specific APIs into these records."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_symbols(self) -> list[ProviderSymbol]:
        raise NotImplementedError

    @abstractmethod
    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        raise NotImplementedError

    @abstractmethod
    def get_daily_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderStockBar]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        raise NotImplementedError

    @abstractmethod
    def get_fund_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderFundPrice]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class NormalizedContext:
    asset_id: UUID
    provider: str
    ingested_at: datetime
