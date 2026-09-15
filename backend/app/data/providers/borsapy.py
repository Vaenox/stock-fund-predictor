from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

import borsapy as bp

from .base import MarketDataProvider, ProviderStockBar, ProviderSymbol


class BorsapyProviderError(RuntimeError):
    """Raised when the borsapy/TradingView source cannot provide usable data."""


@dataclass(frozen=True, slots=True)
class LiveQuote:
    provider: str
    provider_symbol: str
    price: Decimal
    timestamp: datetime | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: Decimal | None = None
    change_percent: Decimal | None = None
    raw: dict[str, Any] | None = None


class BorsapyProvider(MarketDataProvider):
    """BIST provider backed by borsapy and its TradingView WebSocket stream."""

    def __init__(self, *, stream_factory: Callable[[], Any] | None = None) -> None:
        self._stream_factory = stream_factory or bp.TradingViewStream
        self._stream: Any | None = None

    @property
    def name(self) -> str:
        return "borsapy"

    def list_symbols(self) -> list[ProviderSymbol]:
        try:
            companies = bp.companies()
        except Exception as exc:
            raise BorsapyProviderError("Unable to load BIST company list") from exc

        if companies is None or not hasattr(companies, "to_dict"):
            raise BorsapyProviderError("Unexpected borsapy company-list response")

        rows = companies.to_dict(orient="records")
        result: list[ProviderSymbol] = []
        for row in rows:
            symbol = str(row.get("symbol", row.get("ticker", ""))).strip().upper()
            if not symbol:
                continue
            result.append(
                ProviderSymbol(
                    provider=self.name,
                    provider_symbol=symbol,
                    canonical_symbol=symbol,
                    name=str(row.get("name", row.get("title", symbol))).strip(),
                    asset_type="STOCK",
                    isin=row.get("isin"),
                    exchange="BIST",
                    currency="TRY",
                )
            )
        return result

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        symbol = provider_symbol.strip().upper()
        try:
            ticker = bp.Ticker(symbol)
            info = ticker.info or {}
        except Exception as exc:
            raise BorsapyProviderError(f"Unable to load metadata for {symbol}") from exc

        return ProviderSymbol(
            provider=self.name,
            provider_symbol=symbol,
            canonical_symbol=symbol,
            name=str(info.get("shortName", info.get("longName", symbol))),
            asset_type="STOCK",
            isin=info.get("isin"),
            exchange="BIST",
            currency=str(info.get("currency", "TRY")).upper(),
        )

    def get_daily_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderStockBar]:
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        try:
            frame = bp.Ticker(provider_symbol.strip().upper()).history(
                start=start_date.isoformat(), end=end_date.isoformat(), interval="1d"
            )
        except Exception as exc:
            raise BorsapyProviderError(
                f"Unable to load history for {provider_symbol}"
            ) from exc

        if frame is None or frame.empty:
            return []

        result: list[ProviderStockBar] = []
        for index, row in frame.iterrows():
            trading_date = index.date() if isinstance(index, datetime) else index
            result.append(
                ProviderStockBar(
                    provider_symbol=provider_symbol.strip().upper(),
                    trading_date=trading_date,
                    open=Decimal(str(row["Open"])),
                    high=Decimal(str(row["High"])),
                    low=Decimal(str(row["Low"])),
                    close=Decimal(str(row["Close"])),
                    adjusted_close=(
                        Decimal(str(row["Adj Close"]))
                        if "Adj Close" in row and row["Adj Close"] is not None
                        else None
                    ),
                    volume=(
                        Decimal(str(row["Volume"]))
                        if "Volume" in row and row["Volume"] is not None
                        else None
                    ),
                    source_timestamp=None,
                    raw={"provider": self.name},
                )
            )
        return result

    def connect_stream(self) -> None:
        if self._stream is None:
            self._stream = self._stream_factory()
            self._stream.connect()

    def subscribe(self, symbols: list[str]) -> None:
        self.connect_stream()
        for symbol in symbols:
            self._stream.subscribe(symbol.strip().upper())

    def get_live_quote(self, provider_symbol: str, *, timeout: float = 5.0) -> LiveQuote:
        self.connect_stream()
        symbol = provider_symbol.strip().upper()
        quote = self._stream.wait_for_quote(symbol, timeout=timeout)
        if not quote or quote.get("last") is None:
            raise BorsapyProviderError(f"No live quote received for {symbol}")

        raw_timestamp = quote.get("timestamp")
        timestamp: datetime | None = None
        if raw_timestamp is not None:
            try:
                timestamp = datetime.fromtimestamp(float(raw_timestamp))
            except (TypeError, ValueError, OSError):
                timestamp = None

        def dec(key: str) -> Decimal | None:
            value = quote.get(key)
            return Decimal(str(value)) if value is not None else None

        return LiveQuote(
            provider=self.name,
            provider_symbol=symbol,
            price=Decimal(str(quote["last"])),
            timestamp=timestamp,
            bid=dec("bid"),
            ask=dec("ask"),
            volume=dec("volume"),
            change_percent=dec("change_percent"),
            raw=dict(quote),
        )

    def on_any_quote(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        self.connect_stream()
        self._stream.on_any_quote(callback)

    def disconnect_stream(self) -> None:
        if self._stream is not None:
            self._stream.disconnect()
            self._stream = None

    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        quote = self.get_live_quote(provider_symbol)
        today = quote.timestamp.date() if quote.timestamp else date.today()
        return ProviderStockBar(
            provider_symbol=quote.provider_symbol,
            trading_date=today,
            open=quote.price,
            high=quote.price,
            low=quote.price,
            close=quote.price,
            volume=quote.volume,
            source_timestamp=quote.timestamp,
            raw=quote.raw,
        )

    def get_fund_history(self, provider_symbol: str, start_date: date, end_date: date):
        raise NotImplementedError("BorsapyProvider is only for BIST stocks")

    def health_check(self) -> bool:
        try:
            symbols = self.list_symbols()
            return len(symbols) > 0
        except BorsapyProviderError:
            return False
