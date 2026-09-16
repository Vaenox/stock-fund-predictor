from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Any, Callable

from app.data.providers.base import ProviderSymbol

from .types import LiveCandleEvent, LiveQuoteEvent


class BistStreamManagerError(RuntimeError):
    """Raised when the BIST streaming manager cannot operate the stream."""


QuoteCallback = Callable[[LiveQuoteEvent], None]
CandleCallback = Callable[[LiveCandleEvent], None]


class BistStreamManager:
    """Manage one persistent TradingView stream for many BIST symbols.

    The manager deliberately keeps provider-specific callback payloads at the
    boundary. Downstream consumers receive only canonical event DTOs.
    """

    def __init__(
        self,
        *,
        provider_name: str,
        stream_factory: Callable[[], Any],
        symbols: list[ProviderSymbol] | None = None,
    ) -> None:
        self._provider_name = provider_name
        self._stream_factory = stream_factory
        self._stream: Any | None = None
        self._lock = RLock()
        self._symbols: dict[str, ProviderSymbol] = {}
        self._quote_subscribed: set[str] = set()
        self._candle_subscribed: set[tuple[str, str]] = set()
        self._quote_callbacks: list[QuoteCallback] = []
        self._candle_callbacks: list[CandleCallback] = []

        if symbols:
            self.set_symbols(symbols)

    @property
    def is_connected(self) -> bool:
        return self._stream is not None

    @property
    def known_symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._symbols))

    @property
    def subscribed_symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._quote_subscribed))

    def set_symbols(self, symbols: list[ProviderSymbol]) -> None:
        """Replace the local provider-symbol → canonical-symbol registry."""
        registry: dict[str, ProviderSymbol] = {}
        for symbol in symbols:
            provider_symbol = symbol.provider_symbol.strip().upper()
            if not provider_symbol:
                continue
            registry[provider_symbol] = symbol
        self._symbols = registry

    def add_quote_callback(self, callback: QuoteCallback) -> None:
        if callback not in self._quote_callbacks:
            self._quote_callbacks.append(callback)

    def add_candle_callback(self, callback: CandleCallback) -> None:
        if callback not in self._candle_callbacks:
            self._candle_callbacks.append(callback)

    def start(self, symbols: list[str] | None = None) -> None:
        """Connect once and subscribe to the requested quote symbols."""
        with self._lock:
            if self._stream is None:
                try:
                    self._stream = self._stream_factory()
                    self._stream.connect()
                    self._stream.on_any_quote(self._handle_quote)
                    self._stream.on_any_candle(self._handle_candle)
                except Exception as exc:
                    self._stream = None
                    raise BistStreamManagerError("Unable to start TradingView stream") from exc

            requested = symbols if symbols is not None else list(self._symbols)
            self._subscribe_quotes(requested)

    def subscribe_quotes(self, symbols: list[str]) -> None:
        self.start(symbols)

    def subscribe_candles(self, symbols: list[str], interval: str = "1m") -> None:
        if not interval:
            raise ValueError("interval cannot be empty")
        with self._lock:
            self.start([])
            try:
                for symbol in self._normalize_symbols(symbols):
                    subscription = (symbol, interval)
                    if subscription in self._candle_subscribed:
                        continue
                    self._stream.subscribe_chart(symbol, interval)
                    self._candle_subscribed.add(subscription)
            except Exception as exc:
                raise BistStreamManagerError(
                    f"Unable to subscribe candle stream ({interval})"
                ) from exc

    def stop(self) -> None:
        with self._lock:
            if self._stream is None:
                return
            stream = self._stream
            self._stream = None
            self._quote_subscribed.clear()
            self._candle_subscribed.clear()
            try:
                stream.disconnect()
            except Exception as exc:
                raise BistStreamManagerError("Unable to disconnect TradingView stream") from exc

    def _subscribe_quotes(self, symbols: list[str]) -> None:
        normalized = self._normalize_symbols(symbols)
        try:
            for symbol in normalized:
                if symbol in self._quote_subscribed:
                    continue
                self._stream.subscribe(symbol)
                self._quote_subscribed.add(symbol)
        except Exception as exc:
            raise BistStreamManagerError("Unable to subscribe BIST symbols") from exc

    @staticmethod
    def _normalize_symbols(symbols: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for symbol in symbols:
            normalized = symbol.strip().upper()
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
        return result

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, ArithmeticError):
            return None

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    def _canonical_symbol(self, provider_symbol: str) -> str:
        mapping = self._symbols.get(provider_symbol.strip().upper())
        return mapping.canonical_symbol if mapping else provider_symbol.strip().upper()

    def _handle_quote(self, provider_symbol: str, quote: dict[str, Any]) -> None:
        symbol = provider_symbol.strip().upper()
        price = self._decimal(quote.get("last"))
        if price is None:
            return

        event = LiveQuoteEvent(
            event_type="quote",
            provider=self._provider_name,
            provider_symbol=symbol,
            canonical_symbol=self._canonical_symbol(symbol),
            price=price,
            timestamp=self._timestamp(quote.get("timestamp")),
            bid=self._decimal(quote.get("bid")),
            ask=self._decimal(quote.get("ask")),
            volume=self._decimal(quote.get("volume")),
            change_percent=self._decimal(quote.get("change_percent")),
            received_at=datetime.now(timezone.utc),
            raw=dict(quote),
        )
        for callback in tuple(self._quote_callbacks):
            callback(event)

    def _handle_candle(
        self,
        provider_symbol: str,
        interval: str,
        candle: dict[str, Any],
    ) -> None:
        symbol = provider_symbol.strip().upper()
        # borsapy's TradingView candle payload uses `time` as the epoch field.
        # Keep `timestamp` as a compatibility fallback for provider variants.
        timestamp_value = candle.get("time", candle.get("timestamp"))
        timestamp = self._timestamp(timestamp_value)
        open_price = self._decimal(candle.get("open"))
        high = self._decimal(candle.get("high"))
        low = self._decimal(candle.get("low"))
        close = self._decimal(candle.get("close"))
        if timestamp is None or None in (open_price, high, low, close):
            return

        event = LiveCandleEvent(
            event_type="candle",
            provider=self._provider_name,
            provider_symbol=symbol,
            canonical_symbol=self._canonical_symbol(symbol),
            interval=interval,
            timestamp=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=self._decimal(candle.get("volume")),
            received_at=datetime.now(timezone.utc),
            raw=dict(candle),
        )
        for callback in tuple(self._candle_callbacks):
            callback(event)
