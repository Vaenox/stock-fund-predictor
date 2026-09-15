from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterable

import yfinance as yf

from .base import MarketDataProvider, ProviderFundPrice, ProviderStockBar, ProviderSymbol


class YahooFinanceProviderError(RuntimeError):
    """Raised when Yahoo Finance data cannot be converted to provider records."""


@dataclass(frozen=True, slots=True)
class YahooSymbolConfig:
    canonical_symbol: str
    name: str | None = None
    isin: str | None = None


class YahooFinanceProvider(MarketDataProvider):
    """Free-development stock provider using Yahoo Finance via yfinance.

    Symbols are mapped to Yahoo's BIST convention, e.g. THYAO -> THYAO.IS.
    This adapter is intended for personal/development use; replace it with a licensed
    provider before public/commercial redistribution of market data.
    """

    def __init__(self, symbols: Iterable[YahooSymbolConfig] = ()) -> None:
        self._symbols = {item.canonical_symbol.upper(): item for item in symbols}

    @property
    def name(self) -> str:
        return "yahoo_finance"

    @staticmethod
    def yahoo_symbol(provider_symbol: str) -> str:
        symbol = provider_symbol.strip().upper()
        return symbol if symbol.endswith(".IS") else f"{symbol}.IS"

    def list_symbols(self) -> list[ProviderSymbol]:
        return [
            ProviderSymbol(
                provider=self.name,
                provider_symbol=self.yahoo_symbol(item.canonical_symbol),
                canonical_symbol=item.canonical_symbol.upper(),
                name=item.name or item.canonical_symbol.upper(),
                asset_type="STOCK",
                isin=item.isin,
                exchange="BIST",
                currency="TRY",
            )
            for item in self._symbols.values()
        ]

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        canonical = provider_symbol.removesuffix(".IS").upper()
        config = self._symbols.get(canonical, YahooSymbolConfig(canonical_symbol=canonical))
        return ProviderSymbol(
            provider=self.name,
            provider_symbol=self.yahoo_symbol(canonical),
            canonical_symbol=canonical,
            name=config.name or canonical,
            asset_type="STOCK",
            isin=config.isin,
            exchange="BIST",
            currency="TRY",
        )

    def get_daily_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderStockBar]:
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        ticker_symbol = self.yahoo_symbol(provider_symbol)
        try:
            frame = yf.Ticker(ticker_symbol).history(
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=False,
            )
        except Exception as exc:
            raise YahooFinanceProviderError(
                f"Yahoo Finance history request failed: {ticker_symbol}"
            ) from exc

        if frame.empty:
            return []

        records: list[ProviderStockBar] = []
        for index, row in frame.iterrows():
            trading_date = index.date() if hasattr(index, "date") else index
            values = {
                key: row.get(key)
                for key in ("Open", "High", "Low", "Close", "Adj Close", "Volume")
            }
            if any(value is None for value in values.values()):
                continue

            records.append(
                ProviderStockBar(
                    provider_symbol=ticker_symbol,
                    trading_date=trading_date,
                    open=Decimal(str(values["Open"])),
                    high=Decimal(str(values["High"])),
                    low=Decimal(str(values["Low"])),
                    close=Decimal(str(values["Close"])),
                    adjusted_close=Decimal(str(values["Adj Close"])),
                    volume=Decimal(str(values["Volume"])),
                    source_timestamp=datetime.now(timezone.utc),
                    raw={
                        "ticker": ticker_symbol,
                        "date": str(trading_date),
                        "open": values["Open"],
                        "high": values["High"],
                        "low": values["Low"],
                        "close": values["Close"],
                        "adj_close": values["Adj Close"],
                        "volume": values["Volume"],
                    },
                )
            )

        return records

    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        today = datetime.now(timezone.utc).date()
        history = self.get_daily_history(
            provider_symbol,
            today.replace(day=max(1, today.day - 7)),
            today,
        )
        if not history:
            raise YahooFinanceProviderError(
                f"Yahoo Finance latest price not found: {self.yahoo_symbol(provider_symbol)}"
            )
        return history[-1]

    def get_fund_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderFundPrice]:
        raise NotImplementedError("Yahoo Finance provider is stock-only")

    def health_check(self) -> bool:
        try:
            history = self.get_daily_history(
                "THYAO",
                datetime.now(timezone.utc).date().replace(day=1),
                datetime.now(timezone.utc).date(),
            )
            return bool(history)
        except (YahooFinanceProviderError, ValueError):
            return False
