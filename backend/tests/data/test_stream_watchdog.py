from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.data.providers.base import ProviderSymbol
from app.data.streaming.manager import BistStreamManager
from app.data.streaming.watchdog import BistStreamWatchdog


@dataclass
class FakeStream:
    connected: bool = False
    disconnected: bool = False
    quote_subscriptions: list[str] = field(default_factory=list)
    candle_subscriptions: list[tuple[str, str]] = field(default_factory=list)

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.disconnected = True
        self.connected = False

    def subscribe(self, symbol: str) -> None:
        self.quote_subscriptions.append(symbol)

    def subscribe_chart(self, symbol: str, interval: str) -> None:
        self.candle_subscriptions.append((symbol, interval))

    def on_any_quote(self, callback) -> None:
        self.quote_callback = callback

    def on_any_candle(self, callback) -> None:
        self.candle_callback = callback


def symbol(provider_symbol: str) -> ProviderSymbol:
    return ProviderSymbol(
        provider="borsapy",
        provider_symbol=provider_symbol,
        canonical_symbol=provider_symbol,
        name=provider_symbol,
        asset_type="STOCK",
        exchange="BIST",
        currency="TRY",
    )


def test_watchdog_force_reconnect_restores_quote_and_candle_subscriptions():
    created: list[FakeStream] = []

    def factory() -> FakeStream:
        stream = FakeStream()
        created.append(stream)
        return stream

    manager = BistStreamManager(
        provider_name="borsapy",
        stream_factory=factory,
        symbols=[symbol("THYAO")],
    )
    manager.start(["THYAO"])
    manager.subscribe_candles(["THYAO"], "1m")

    watchdog = BistStreamWatchdog(manager)
    watchdog.start(
        quote_symbols=["THYAO"],
        candle_subscriptions=[("THYAO", "1m")],
    )
    watchdog.force_reconnect()
    watchdog.stop()

    assert len(created) == 2
    assert created[0].disconnected is True
    assert created[1].connected is True
    assert created[1].quote_subscriptions == ["THYAO"]
    assert created[1].candle_subscriptions == [("THYAO", "1m")]


def test_watchdog_records_last_quote_event_time():
    stream = FakeStream()
    manager = BistStreamManager(
        provider_name="borsapy",
        stream_factory=lambda: stream,
        symbols=[symbol("THYAO")],
    )
    manager.start(["THYAO"])
    watchdog = BistStreamWatchdog(manager)

    timestamp = datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)
    stream.quote_callback("THYAO", {"last": 300, "timestamp": timestamp.timestamp()})

    assert watchdog.last_event_at["THYAO"] is not None
    assert watchdog.last_event_at["THYAO"].tzinfo == timezone.utc


def test_watchdog_does_not_mark_empty_stream_as_stale():
    stream = FakeStream()
    manager = BistStreamManager(provider_name="borsapy", stream_factory=lambda: stream)
    watchdog = BistStreamWatchdog(manager, stale_after_seconds=0.1, check_interval_seconds=0.1)

    assert watchdog.is_running is False
    manager.start([])
    watchdog.start(quote_symbols=[])
    assert watchdog.is_running is True
    watchdog.stop()
    assert watchdog.is_running is False
