from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.data.providers.base import ProviderSymbol
from app.data.streaming.manager import BistStreamManager
from app.data.streaming.types import LiveCandleEvent, LiveQuoteEvent


@dataclass
class FakeStream:
    connected: bool = False
    disconnected: bool = False
    quote_subscriptions: list[str] = field(default_factory=list)
    candle_subscriptions: list[tuple[str, str]] = field(default_factory=list)
    quote_callback: object | None = None
    candle_callback: object | None = None

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.disconnected = True

    def subscribe(self, symbol: str) -> None:
        self.quote_subscriptions.append(symbol)

    def subscribe_chart(self, symbol: str, interval: str) -> None:
        self.candle_subscriptions.append((symbol, interval))

    def on_any_quote(self, callback) -> None:
        self.quote_callback = callback

    def on_any_candle(self, callback) -> None:
        self.candle_callback = callback


def symbol(provider_symbol: str, canonical_symbol: str) -> ProviderSymbol:
    return ProviderSymbol(
        provider="borsapy",
        provider_symbol=provider_symbol,
        canonical_symbol=canonical_symbol,
        name=canonical_symbol,
        asset_type="STOCK",
        exchange="BIST",
        currency="TRY",
    )


def test_manager_uses_one_persistent_connection_and_idempotent_quote_subscriptions():
    created: list[FakeStream] = []

    def factory() -> FakeStream:
        stream = FakeStream()
        created.append(stream)
        return stream

    manager = BistStreamManager(
        provider_name="borsapy",
        stream_factory=factory,
        symbols=[symbol("thyao", "THYAO"), symbol("garan", "GARAN")],
    )

    manager.start()
    manager.start()

    assert len(created) == 1
    assert created[0].connected is True
    assert created[0].quote_subscriptions == ["THYAO", "GARAN"]
    assert manager.is_connected is True
    assert manager.known_symbols == ("GARAN", "THYAO")
    assert manager.subscribed_symbols == ("GARAN", "THYAO")

    manager.stop()
    assert created[0].disconnected is True
    assert manager.is_connected is False
    assert manager.subscribed_symbols == ()


def test_manager_canonicalizes_quote_and_real_borsapy_candle_events():
    stream = FakeStream()
    manager = BistStreamManager(
        provider_name="borsapy",
        stream_factory=lambda: stream,
        symbols=[symbol("THYAO", "BIST:THYAO")],
    )
    quotes: list[LiveQuoteEvent] = []
    candles: list[LiveCandleEvent] = []
    manager.add_quote_callback(quotes.append)
    manager.add_candle_callback(candles.append)

    manager.start([" thyao "])
    manager.subscribe_candles(["THYAO"], "1m")
    manager.subscribe_candles(["thyao"], "1m")

    assert stream.quote_subscriptions == ["THYAO"]
    assert stream.candle_subscriptions == [("THYAO", "1m")]

    stream.quote_callback(
        "thyao",
        {
            "last": 312.45,
            "bid": 312.4,
            "ask": 312.5,
            "volume": 1000,
            "change_percent": 1.25,
            "timestamp": 1_700_000_000,
        },
    )
    # borsapy/TradingView candle payload uses `time`, not `timestamp`.
    stream.candle_callback(
        "thyao",
        "1m",
        {
            "time": 1_700_000_000,
            "open": 310.0,
            "high": 313.0,
            "low": 309.5,
            "close": 312.45,
            "volume": 250,
        },
    )

    assert quotes[0].canonical_symbol == "BIST:THYAO"
    assert quotes[0].price == Decimal("312.45")
    assert quotes[0].provider_symbol == "THYAO"
    assert quotes[0].timestamp == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)
    assert quotes[0].received_at is not None

    assert candles[0].canonical_symbol == "BIST:THYAO"
    assert candles[0].interval == "1m"
    assert candles[0].timestamp == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)
    assert candles[0].open == Decimal("310.0")
    assert candles[0].close == Decimal("312.45")
    assert candles[0].received_at is not None


def test_manager_ignores_quote_without_last_price():
    stream = FakeStream()
    manager = BistStreamManager(
        provider_name="borsapy",
        stream_factory=lambda: stream,
        symbols=[symbol("THYAO", "THYAO")],
    )
    events: list[LiveQuoteEvent] = []
    manager.add_quote_callback(events.append)
    manager.start(["THYAO"])

    stream.quote_callback("THYAO", {"last": None})

    assert events == []
