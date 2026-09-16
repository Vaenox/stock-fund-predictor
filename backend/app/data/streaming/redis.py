from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from typing import Any

from .types import LiveCandleEvent, LiveQuoteEvent


class RedisStreamPublisherError(RuntimeError):
    """Raised when a live event cannot be published to Redis."""


class RedisLivePublisher:
    """Publish canonical live events to Redis Streams and Pub/Sub channels."""

    QUOTE_STREAM = "market:quotes"
    CANDLE_STREAM = "market:candles"
    QUOTE_CHANNEL = "market:quotes"
    CANDLE_CHANNEL = "market:candles"

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def publish_quote(self, event: LiveQuoteEvent) -> str:
        payload = self._serialize(event)
        return self._publish(self.QUOTE_STREAM, self.QUOTE_CHANNEL, payload)

    def publish_candle(self, event: LiveCandleEvent) -> str:
        payload = self._serialize(event)
        return self._publish(self.CANDLE_STREAM, self.CANDLE_CHANNEL, payload)

    def publish(self, event: LiveQuoteEvent | LiveCandleEvent) -> str:
        if event.event_type == "quote":
            return self.publish_quote(event)
        return self.publish_candle(event)

    def _publish(self, stream_name: str, channel_name: str, payload: dict[str, str]) -> str:
        try:
            event_id = self._redis.xadd(stream_name, payload)
            self._redis.publish(channel_name, json.dumps(payload, separators=(",", ":")))
            return str(event_id)
        except Exception as exc:
            raise RedisStreamPublisherError(
                f"Unable to publish live event to Redis ({stream_name})"
            ) from exc

    @staticmethod
    def _serialize(event: LiveQuoteEvent | LiveCandleEvent) -> dict[str, str]:
        data = asdict(event)
        return {key: RedisLivePublisher._json_value(value) for key, value in data.items()}

    @staticmethod
    def _json_value(value: Any) -> str:
        if isinstance(value, Decimal):
            return str(value)
        if value is None:
            return ""
        if isinstance(value, dict):
            return json.dumps(value, separators=(",", ":"), default=str)
        return str(value)


class RedisLivePublisherProtocol:
    """Small protocol-like surface useful to streaming orchestration code."""

    def publish(self, event: LiveQuoteEvent | LiveCandleEvent) -> str:
        raise NotImplementedError
