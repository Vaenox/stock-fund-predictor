from decimal import Decimal

from app.data.streaming.pipeline import BistRedisPipeline
from app.data.streaming.types import LiveQuoteEvent


class FakeManager:
    def __init__(self):
        self.quote_callbacks = []
        self.candle_callbacks = []
        self.started_with = None
        self.stopped = False

    def add_quote_callback(self, callback):
        self.quote_callbacks.append(callback)

    def add_candle_callback(self, callback):
        self.candle_callbacks.append(callback)

    def start(self, symbols=None):
        self.started_with = symbols

    def stop(self):
        self.stopped = True


class FakePublisher:
    def __init__(self):
        self.quotes = []
        self.candles = []

    def publish_quote(self, event):
        self.quotes.append(event)
        return "1-0"

    def publish_candle(self, event):
        self.candles.append(event)
        return "1-0"


def test_pipeline_registers_callbacks_and_publishes_quote():
    manager = FakeManager()
    publisher = FakePublisher()
    pipeline = BistRedisPipeline(manager, publisher)

    pipeline.start(["THYAO", "GARAN"])
    assert manager.started_with == ["THYAO", "GARAN"]

    event = LiveQuoteEvent(
        event_type="quote",
        provider="borsapy",
        provider_symbol="THYAO",
        canonical_symbol="THYAO",
        price=Decimal("312.45"),
    )
    manager.quote_callbacks[0](event)

    assert publisher.quotes == [event]


def test_pipeline_is_idempotent_and_stops_manager():
    manager = FakeManager()
    publisher = FakePublisher()
    pipeline = BistRedisPipeline(manager, publisher)

    pipeline.start(["THYAO"])
    pipeline.start(["GARAN"])
    pipeline.stop()
    pipeline.stop()

    assert manager.started_with == ["THYAO"]
    assert manager.stopped is True
