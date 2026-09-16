from __future__ import annotations

from typing import Any

from sqlalchemy import text

from .types import LiveCandleEvent, LiveQuoteEvent


class LiveMarketPersistence:
    """Persist canonical live events and configure Timescale retention policies."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    def store_quote(self, asset_id: Any, event: LiveQuoteEvent) -> None:
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO stock_live_ticks
                        (asset_id, occurred_at, price, bid, ask, volume,
                         change_percent, source_provider, received_at)
                    VALUES
                        (:asset_id, :occurred_at, :price, :bid, :ask, :volume,
                         :change_percent, :source_provider, :received_at)
                    ON CONFLICT (asset_id, occurred_at) DO UPDATE SET
                        price = EXCLUDED.price,
                        bid = EXCLUDED.bid,
                        ask = EXCLUDED.ask,
                        volume = EXCLUDED.volume,
                        change_percent = EXCLUDED.change_percent,
                        source_provider = EXCLUDED.source_provider,
                        received_at = EXCLUDED.received_at
                    """
                ),
                {
                    "asset_id": asset_id,
                    "occurred_at": event.timestamp or event.received_at,
                    "price": event.price,
                    "bid": event.bid,
                    "ask": event.ask,
                    "volume": event.volume,
                    "change_percent": event.change_percent,
                    "source_provider": event.provider,
                    "received_at": event.received_at,
                },
            )
            session.commit()

    def store_candle(self, asset_id: Any, event: LiveCandleEvent) -> None:
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO stock_live_candles
                        (asset_id, interval, occurred_at, open, high, low, close,
                         volume, source_provider, received_at)
                    VALUES
                        (:asset_id, :interval, :occurred_at, :open, :high, :low, :close,
                         :volume, :source_provider, :received_at)
                    ON CONFLICT (asset_id, interval, occurred_at) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        source_provider = EXCLUDED.source_provider,
                        received_at = EXCLUDED.received_at
                    """
                ),
                {
                    "asset_id": asset_id,
                    "interval": event.interval,
                    "occurred_at": event.timestamp,
                    "open": event.open,
                    "high": event.high,
                    "low": event.low,
                    "close": event.close,
                    "volume": event.volume,
                    "source_provider": event.provider,
                    "received_at": event.received_at,
                },
            )
            session.commit()

    @staticmethod
    def configure_retention(bind: Any, *, tick_days: int = 30, candle_days: int = 180) -> None:
        if tick_days < 1 or candle_days < 1:
            raise ValueError("retention periods must be positive")
        if bind.dialect.name != "postgresql":
            return

        # Values are validated integers above, so interpolation keeps the
        # TimescaleDB interval syntax simple and avoids driver-specific bind
        # handling inside a PostgreSQL DO block.
        bind.execute(
            text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                        PERFORM add_retention_policy(
                            'stock_live_ticks',
                            INTERVAL '{tick_days} days',
                            if_not_exists => TRUE
                        );
                        PERFORM add_retention_policy(
                            'stock_live_candles',
                            INTERVAL '{candle_days} days',
                            if_not_exists => TRUE
                        );
                    END IF;
                END $$;
                """
            )
        )
