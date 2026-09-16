from __future__ import annotations

from .manager import BistStreamManager
from .redis import RedisLivePublisher
from .types import LiveCandleEvent, LiveQuoteEvent


class BistRedisPipeline:
    """Bridge canonical BIST stream events into Redis."""

    def __init__(self, manager: BistStreamManager, publisher: RedisLivePublisher) -> None:
        self._manager = manager
        self._publisher = publisher
        self._started = False

    def start(self, symbols: list[str] | None = None) -> None:
        if self._started:
            return
        self._manager.add_quote_callback(self._publish_quote)
        self._manager.add_candle_callback(self._publish_candle)
        self._manager.start(symbols)
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._manager.stop()
        self._started = False

    def _publish_quote(self, event: LiveQuoteEvent) -> None:
        self._publisher.publish_quote(event)

    def _publish_candle(self, event: LiveCandleEvent) -> None:
        self._publisher.publish_candle(event)
