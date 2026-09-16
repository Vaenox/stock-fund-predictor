from __future__ import annotations

import argparse
import sys
from datetime import date

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data.incremental import ingest_stock_incremental
from app.data.providers.borsapy import BorsapyProvider
from app.models.market_data import Asset, AssetProviderMapping, AssetStatus, AssetType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real incremental BIST historical-ingestion smoke test."
    )
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--bootstrap-days", type=int, default=30)
    parser.add_argument("--overlap-days", type=int, default=1)
    return parser.parse_args()


def _ensure_schema(engine) -> None:
    required = {"assets", "asset_provider_mappings", "stock_daily_bars"}
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


def main() -> int:
    args = parse_args()
    symbol = args.symbol.strip().upper()
    if not symbol or args.bootstrap_days < 1 or args.overlap_days < 0:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    engine = create_engine(get_settings().database_url, future=True)
    provider = BorsapyProvider()

    try:
        _ensure_schema(engine)
        with Session(engine) as session:
            asset = _ensure_asset(session, symbol)
            _ensure_mapping(session, asset, provider.name, symbol)
            asset_id = asset.id

            previous_last = session.scalar(
                text(
                    "SELECT MAX(trading_date) FROM stock_daily_bars "
                    "WHERE asset_id = :asset_id"
                ),
                {"asset_id": asset_id},
            )
            before_count = session.scalar(
                text("SELECT COUNT(*) FROM stock_daily_bars WHERE asset_id = :asset_id"),
                {"asset_id": asset_id},
            )

            result = ingest_stock_incremental(
                session,
                provider,
                asset_id=asset_id,
                provider_symbol=symbol,
                as_of=date.today(),
                bootstrap_days=args.bootstrap_days,
                overlap_days=args.overlap_days,
            )

            after_count = session.scalar(
                text("SELECT COUNT(*) FROM stock_daily_bars WHERE asset_id = :asset_id"),
                {"asset_id": asset_id},
            )
            after_last = session.scalar(
                text(
                    "SELECT MAX(trading_date) FROM stock_daily_bars "
                    "WHERE asset_id = :asset_id"
                ),
                {"asset_id": asset_id},
            )
    except Exception as exc:
        print(f"INCREMENTAL SMOKE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Symbol: {symbol}")
    print(
        f"Previous last date: {previous_last} | "
        f"Incremental window: {result.start_date}->{result.end_date} | "
        f"bootstrap={result.bootstrap} overlap_days={result.overlap_days}"
    )
    print(
        f"Ingestion: received={result.ingestion.received} "
        f"written={result.ingestion.written}"
    )
    print(f"DB rows: before={before_count} after={after_count}")
    print(f"Latest persisted date: {after_last}")

    expected_start = (
        result.end_date
        if previous_last is None
        else previous_last
    )
    if previous_last is None:
        if not result.bootstrap:
            print("INCREMENTAL SMOKE FAILED: expected bootstrap mode", file=sys.stderr)
            return 1
    else:
        if result.bootstrap or result.start_date > expected_start:
            print("INCREMENTAL SMOKE FAILED: incremental window did not resume from persisted data", file=sys.stderr)
            return 1

    if after_last is None or after_last > result.end_date:
        print("INCREMENTAL SMOKE FAILED: invalid persisted upper bound", file=sys.stderr)
        return 1

    print("INCREMENTAL INGESTION SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
