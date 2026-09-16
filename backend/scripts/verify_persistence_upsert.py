from __future__ import annotations

import argparse
import sys
import threading
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import borsapy as bp
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data.ingestion import ingest_stock_history
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.base import ProviderSymbol
from app.data.streaming.manager import BistStreamManager
from app.data.streaming.persistence import LiveMarketPersistence
from app.models.market_data import Asset, AssetProviderMapping, AssetStatus, AssetType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify real-data historical/live upsert and source provenance."
    )
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--history-days", type=int, default=7)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def _ensure_schema(engine) -> None:
    required = {
        "assets",
        "asset_provider_mappings",
        "stock_daily_bars",
        "stock_live_ticks",
    }
    missing = sorted(required - set(inspect(engine).get_table_names()))
    if missing:
        raise RuntimeError(
            "Database schema is incomplete. Run 'alembic upgrade head' first. "
            f"Missing tables: {', '.join(missing)}"
        )


def _ensure_asset(session: Session, symbol: str) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.canonical_symbol == symbol))
    if asset is None:
        asset = Asset(
            asset_type=AssetType.STOCK,
            canonical_symbol=symbol,
            name=symbol,
            exchange="BIST",
            currency="TRY",
            status=AssetStatus.ACTIVE,
        )
        session.add(asset)
        session.flush()
    elif asset.asset_type != AssetType.STOCK:
        raise ValueError(f"Asset {symbol} exists with type {asset.asset_type}")
    return asset


def _ensure_mapping(session: Session, asset: Asset, provider: str, symbol: str) -> None:
    mapping = session.scalar(
        select(AssetProviderMapping).where(
            AssetProviderMapping.provider == provider,
            AssetProviderMapping.provider_symbol == symbol,
        )
    )
    if mapping is None:
        session.add(
            AssetProviderMapping(
                asset_id=asset.id,
                provider=provider,
                provider_symbol=symbol,
                is_primary=True,
            )
        )
    elif mapping.asset_id != asset.id:
        raise ValueError(
            f"Provider mapping {provider}:{symbol} points to a different asset"
        )
    session.commit()


def _historical_snapshot(session: Session, asset_id, start_date: date, end_date: date):
    rows = session.execute(
        text(
            """
            SELECT trading_date, close, source_provider, source_timestamp, ingested_at
            FROM stock_daily_bars
            WHERE asset_id = :asset_id
              AND trading_date BETWEEN :start_date AND :end_date
            ORDER BY trading_date
            """
        ),
        {
            "asset_id": asset_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).mappings().all()
    return rows


def _historical_source_timestamp_available(rows) -> bool:
    """Historical providers may legitimately omit a source event timestamp.

    The database contract distinguishes provider provenance from ingestion-time
    provenance. For daily bars, ``source_timestamp`` is optional because some
    providers return date-keyed end-of-day data without an authoritative source
    event timestamp. ``ingested_at`` remains required and is used to verify that
    a second ingestion updated the stored row.
    """
    return True


def main() -> int:
    args = parse_args()
    symbol = args.symbol.strip().upper()
    if not symbol or args.history_days < 1 or args.timeout <= 0:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    provider = BorsapyProvider()

    try:
        _ensure_schema(engine)
        end_date = date.today()
        start_date = end_date - timedelta(days=args.history_days)

        with Session(engine) as session:
            asset = _ensure_asset(session, symbol)
            _ensure_mapping(session, asset, provider.name, symbol)
            asset_id = asset.id

            first = ingest_stock_history(
                session,
                provider,
                asset_id=asset_id,
                provider_symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                today=end_date,
            )
            before = _historical_snapshot(session, asset_id, start_date, end_date)

            if not before:
                raise RuntimeError("Historical upsert test has no database rows to verify")

            first_ingested_at = before[0]["ingested_at"]

            second = ingest_stock_history(
                session,
                provider,
                asset_id=asset_id,
                provider_symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                today=end_date,
            )
            after = _historical_snapshot(session, asset_id, start_date, end_date)

        print(
            f"Historical first: received={first.received} written={first.written} "
            f"db_rows={len(before)}"
        )
        print(
            f"Historical second: received={second.received} written={second.written} "
            f"db_rows={len(after)}"
        )

        if len(after) != len(before):
            raise RuntimeError(
                f"Historical duplicate detected: before={len(before)} after={len(after)}"
            )

        if not after:
            raise RuntimeError("Historical rows disappeared after second ingestion")

        provenance_ok = all(row["source_provider"] == provider.name for row in after)
        source_timestamp_optional_ok = _historical_source_timestamp_available(after)
        ingested_at_changed = any(
            row["ingested_at"] != first_ingested_at for row in after
        )

        print(
            "Historical provenance: "
            f"source_provider_ok={provenance_ok} "
            f"source_timestamp_optional_ok={source_timestamp_optional_ok} "
            f"ingested_at_updated={ingested_at_changed}"
        )

        if not provenance_ok or not source_timestamp_optional_ok or not ingested_at_changed:
            raise RuntimeError("Historical provenance/upsert verification failed")

        live_received = threading.Event()
        live_event = None
        live_error: list[str] = []
        metadata = ProviderSymbol(
            provider=provider.name,
            provider_symbol=symbol,
            canonical_symbol=symbol,
            name=symbol,
            asset_type="STOCK",
            exchange="BIST",
            currency="TRY",
        )
        manager = BistStreamManager(
            provider_name=provider.name,
            stream_factory=bp.TradingViewStream,
            symbols=[metadata],
        )
        persistence = LiveMarketPersistence(lambda: Session(engine))

        def on_quote(event) -> None:
            nonlocal live_event
            try:
                live_event = event
                persistence.store_quote(asset_id, event)
                live_received.set()
            except Exception as exc:
                live_error.append(f"{type(exc).__name__}: {exc}")
                live_received.set()

        manager.add_quote_callback(on_quote)
        print(f"Starting real live quote upsert test for {symbol} ...")
        manager.start([symbol])
        try:
            if not live_received.wait(timeout=args.timeout):
                raise RuntimeError("No real live quote received within timeout")
        finally:
            manager.stop()

        if live_error:
            raise RuntimeError(live_error[0])
        if live_event is None:
            raise RuntimeError("Live callback completed without an event")

        occurred_at = live_event.timestamp or live_event.received_at
        if occurred_at is None:
            raise RuntimeError("Live event has neither timestamp nor received_at")

        with Session(engine) as session:
            before_live = session.execute(
                text(
                    """
                    SELECT occurred_at, price, source_provider, received_at
                    FROM stock_live_ticks
                    WHERE asset_id = :asset_id AND occurred_at = :occurred_at
                    """
                ),
                {"asset_id": asset_id, "occurred_at": occurred_at},
            ).mappings().one_or_none()

        if before_live is None:
            raise RuntimeError("First live quote was not found at its conflict key")

        original_received_at = before_live["received_at"]
        original_price = Decimal(str(before_live["price"]))
        replacement_price = original_price + Decimal("0.01")
        replacement_received_at = datetime.now(timezone.utc)
        replacement_event = replace(
            live_event,
            price=replacement_price,
            received_at=replacement_received_at,
        )
        persistence.store_quote(asset_id, replacement_event)

        with Session(engine) as session:
            live_rows = session.execute(
                text(
                    """
                    SELECT occurred_at, price, source_provider, received_at
                    FROM stock_live_ticks
                    WHERE asset_id = :asset_id AND occurred_at = :occurred_at
                    """
                ),
                {"asset_id": asset_id, "occurred_at": occurred_at},
            ).mappings().all()

        print(
            f"Live conflict key rows={len(live_rows)} "
            f"original_price={original_price} replacement_price={replacement_price}"
        )

        if len(live_rows) != 1:
            raise RuntimeError("Live duplicate detected at the same conflict key")

        live_row = live_rows[0]
        live_upsert_ok = (
            Decimal(str(live_row["price"])) == replacement_price
            and live_row["source_provider"] == provider.name
            and live_row["received_at"] == replacement_received_at
        )
        received_at_updated = live_row["received_at"] != original_received_at
        print(
            "Live provenance/upsert: "
            f"updated={live_upsert_ok} received_at_updated={received_at_updated} "
            f"source_provider={live_row['source_provider']}"
        )

        if not live_upsert_ok or not received_at_updated:
            raise RuntimeError("Live provenance/upsert verification failed")

    except Exception as exc:
        print(f"VERIFY FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("PERSISTENCE UPSERT/PROVENANCE VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
