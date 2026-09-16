from __future__ import annotations

import argparse
import sys
import threading
from datetime import date, timedelta

import borsapy as bp
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data.ingestion import ingest_stock_history
from app.data.providers.base import ProviderSymbol
from app.data.providers.borsapy import BorsapyProvider
from app.data.streaming.manager import BistStreamManager
from app.models.market_data import Asset, AssetProviderMapping, AssetStatus, AssetType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persist real BIST historical + live data and verify the database write path."
    )
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--history-days", type=int, default=7)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def _ensure_schema(engine) -> None:
    inspector = inspect(engine)
    required = {
        "assets",
        "asset_provider_mappings",
        "stock_daily_bars",
        "stock_live_ticks",
    }
    missing = sorted(required - set(inspector.get_table_names()))
    if missing:
        raise RuntimeError(
            "Database schema is incomplete. Run 'alembic upgrade head' first. "
            f"Missing tables: {', '.join(missing)}"
        )


def _ensure_asset(session: Session, symbol: str) -> Asset:
    asset = session.scalar(
        select(Asset).where(Asset.canonical_symbol == symbol)
    )
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
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    metadata = ProviderSymbol(
        provider=provider.name,
        provider_symbol=symbol,
        canonical_symbol=symbol,
        name=symbol,
        asset_type="STOCK",
        exchange="BIST",
        currency="TRY",
    )

    with Session(engine) as session:
        asset = _ensure_asset(session, symbol)
        _ensure_mapping(session, asset, provider.name, symbol)
        asset_id = asset.id

        end_date = date.today()
        start_date = end_date - timedelta(days=args.history_days)
        result = ingest_stock_history(
            session,
            provider,
            asset_id=asset_id,
            provider_symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            today=end_date,
        )

        historical_count = session.scalar(
            text(
                "SELECT COUNT(*) FROM stock_daily_bars "
                "WHERE asset_id = :asset_id AND trading_date BETWEEN :start_date AND :end_date"
            ),
            {
                "asset_id": asset_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

    print(
        f"Historical {symbol}: received={result.received} written={result.written} "
        f"db_rows={historical_count} window={start_date}->{end_date}"
    )

    live_received = threading.Event()
    live_errors: list[str] = []

    manager = BistStreamManager(
        provider_name=provider.name,
        stream_factory=bp.TradingViewStream,
        symbols=[metadata],
    )

    def on_quote(event) -> None:
        try:
            from app.data.streaming.persistence import LiveMarketPersistence

            LiveMarketPersistence(lambda: Session(engine)).store_quote(asset_id, event)
            live_received.set()
        except Exception as exc:
            live_errors.append(f"{type(exc).__name__}: {exc}")
            live_received.set()

    manager.add_quote_callback(on_quote)

    print(f"Starting real live quote persistence test for {symbol} ...")
    try:
        manager.start([symbol])
        if not live_received.wait(timeout=args.timeout):
            print(
                "ERROR: no live quote was persisted within the timeout",
                file=sys.stderr,
            )
            return 1
    except Exception as exc:
        print(f"ERROR: live stream failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        manager.stop()

    if live_errors:
        print(f"ERROR: live persistence failed: {live_errors[0]}", file=sys.stderr)
        return 1

    with Session(engine) as session:
        live_count = session.scalar(
            text(
                "SELECT COUNT(*) FROM stock_live_ticks "
                "WHERE asset_id = :asset_id AND source_provider = :provider"
            ),
            {"asset_id": asset_id, "provider": provider.name},
        )
        latest = session.execute(
            text(
                "SELECT occurred_at, price, source_provider "
                "FROM stock_live_ticks "
                "WHERE asset_id = :asset_id "
                "ORDER BY occurred_at DESC LIMIT 1"
            ),
            {"asset_id": asset_id},
        ).mappings().first()

    print(f"Live ticks db_rows={live_count}")
    if latest:
        print(
            f"Latest live row: occurred_at={latest['occurred_at']} "
            f"price={latest['price']} source_provider={latest['source_provider']}"
        )

    if result.written <= 0 or not latest:
        print("SMOKE TEST FAILED: expected historical and live rows in PostgreSQL", file=sys.stderr)
        return 1

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
