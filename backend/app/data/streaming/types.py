from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal


LiveEventType = Literal["quote", "candle"]


@dataclass(frozen=True, slots=True)
class LiveQuoteEvent:
    """Canonical internal representation of a streamed stock quote."""

    event_type: Literal["quote"]
    provider: str
    provider_symbol: str
    canonical_symbol: str
    price: Decimal
    timestamp: datetime | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: Decimal | None = None
    change_percent: Decimal | None = None
    received_at: datetime | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class LiveCandleEvent:
    """Canonical internal representation of a streamed OHLCV candle."""

    event_type: Literal["candle"]
    provider: str
    provider_symbol: str
    canonical_symbol: str
    interval: str
    timestamp: datetime | None
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    received_at: datetime | None = None
    raw: dict[str, Any] | None = None
