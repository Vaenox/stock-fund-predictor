from datetime import datetime, timezone
from decimal import Decimal

from app.data.streaming.redis import RedisLivePublisher
from app.data.streaming.types import LiveQuoteEvent


class FakeRedis:
    def __init__(self):
        self.streams = []
        self.channels = []

    def xadd(self, stream, payload):
        self.streams.append((stream, payload))
        return "1-0"

    def publish(self, channel, payload):
        self.channels.append((channel, payload))
        return 1


def test_publish_quote_writes_stream_and_pubsub():
    redis = FakeRedis()
    publisher = RedisLivePublisher(redis)
    event = LiveQuoteEvent(
        event_type="quote",
        provider="borsapy",
        provider_symbol="THYAO",
        canonical_symbol="THYAO",
        price=Decimal("312.45"),
        timestamp=datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc),
        bid=Decimal("312.40"),
        ask=Decimal("312.50"),
        volume=Decimal("1000"),
        change_percent=Decimal("1.25"),
        received_at=datetime(2026, 9, 16, 8, 0, 1, tzinfo=timezone.utc),
        raw={"last": 312.45},
    )

    event_id = publisher.publish_quote(event)

    assert event_id == "1-0"
    assert redis.streams[0][0] == "market:quotes"
    assert redis.streams[0][1]["price"] == "312.45"
    assert redis.channels[0][0] == "market:quotes"
    assert '"canonical_symbol":"THYAO"' in redis.channels[0][1]


def test_publish_dispatches_by_event_type():
    redis = FakeRedis()
    publisher = RedisLivePublisher(redis)
    event = LiveQuoteEvent(
        event_type="quote",
        provider="borsapy",
        provider_symbol="GARAN",
        canonical_symbol="GARAN",
        price=Decimal("160"),
    )

    publisher.publish(event)

    assert redis.streams[0][0] == "market:quotes"
