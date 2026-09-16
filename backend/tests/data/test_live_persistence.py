from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.data.streaming.persistence import LiveMarketPersistence
from app.data.streaming.types import LiveCandleEvent, LiveQuoteEvent


class FakeSession:
    def __init__(self):
        self.executed = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params))

    def commit(self):
        self.committed = True


def test_store_quote_uses_upsert_and_event_timestamp():
    session = FakeSession()
    persistence = LiveMarketPersistence(lambda: session)
    timestamp = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)
    event = LiveQuoteEvent(
        event_type="quote",
        provider="borsapy",
        provider_symbol="THYAO",
        canonical_symbol="THYAO",
        price=Decimal("312.45"),
        timestamp=timestamp,
        received_at=timestamp,
    )

    persistence.store_quote("asset-id", event)

    sql, params = session.executed[0]
    assert "ON CONFLICT (asset_id, occurred_at) DO UPDATE" in sql
    assert params["occurred_at"] == timestamp
    assert params["price"] == Decimal("312.45")
    assert session.committed is True


def test_store_candle_uses_interval_in_composite_key():
    session = FakeSession()
    persistence = LiveMarketPersistence(lambda: session)
    timestamp = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)
    event = LiveCandleEvent(
        event_type="candle",
        provider="borsapy",
        provider_symbol="GARAN",
        canonical_symbol="GARAN",
        interval="1m",
        timestamp=timestamp,
        open=Decimal("160"),
        high=Decimal("161"),
        low=Decimal("159"),
        close=Decimal("160.5"),
    )

    persistence.store_candle("asset-id", event)

    sql, params = session.executed[0]
    assert "ON CONFLICT (asset_id, interval, occurred_at) DO UPDATE" in sql
    assert params["interval"] == "1m"
    assert params["close"] == Decimal("160.5")
    assert session.committed is True


def test_configure_retention_is_noop_for_non_postgres():
    bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    LiveMarketPersistence.configure_retention(bind, tick_days=30, candle_days=180)
