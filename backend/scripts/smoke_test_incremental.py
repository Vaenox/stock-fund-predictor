from __future__ import annotations

import argparse
import sys
from datetime import date

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data.incremental import ingest_fund_incremental, ingest_stock_incremental
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.models.market_data import Asset, AssetProviderMapping, AssetStatus, AssetType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real incremental BIST or TEFAS historical-ingestion smoke test."
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--symbol", help="BIST stock symbol (default: THYAO)")
    target.add_argument("--fund-code", help="TEFAS fund code")
    parser.add_argument("--bootstrap-days", type=int, default=30)
    parser.add_argument("--overlap-days", type=int, default=1)
    return parser.parse_args()


def _ensure_schema(engine, asset_type: AssetType) -> None:
    required = {
        "assets",
        "asset_provider_mappings",
        "fund_daily_prices" if asset_type == AssetType.FUND else "stock_daily_bars",
    }
    missing = sorted(required - set(inspect(engine).get_table_names()))
    if missing:
        raise RuntimeError(
            "Database schema is incomplete. Run 'alembic upgrade head' first. "
            f"Missing tables: {', '.join(missing)}"
        )


def _ensure_asset(session: Session, identifier: str, asset_type: AssetType) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.canonical_symbol == identifier))
    if asset is None:
        asset = Asset(
            asset_type=asset_type,
            canonical_symbol=identifier,
            name=identifier,
            exchange="TEFAS" if asset_type == AssetType.FUND else "BIST",
            currency="TRY",
            status=AssetStatus.ACTIVE,
        )
        session.add(asset)
        session.flush()
    elif asset.asset_type != asset_type:
        raise ValueError(f"Asset {identifier} exists with type {asset.asset_type}")
    return asset


def _ensure_mapping(
    session: Session,
    asset: Asset,
    provider: str,
    provider_symbol: str,
) -> None:
    mapping = session.scalar(
        select(AssetProviderMapping).where(
            AssetProviderMapping.provider == provider,
            AssetProviderMapping.provider_symbol == provider_symbol,
        )
    )
    if mapping is None:
        session.add(
            AssetProviderMapping(
                asset_id=asset.id,
                provider=provider,
                provider_symbol=provider_symbol,
                is_primary=True,
            )
        )
    elif mapping.asset_id != asset.id:
        raise ValueError(
            f"Provider mapping {provider}:{provider_symbol} points to a different asset"
        )
    session.commit()


def main() -> int:
    args = parse_args()

    is_fund = args.fund_code is not None
    identifier = (args.fund_code if is_fund else (args.symbol or "THYAO")).strip().upper()
    asset_type = AssetType.FUND if is_fund else AssetType.STOCK

    if not identifier or args.bootstrap_days < 1 or args.overlap_days < 0:
        print("ERROR: invalid test configuration", file=sys.stderr)
        return 2

    engine = create_engine(get_settings().database_url, future=True)
    provider = TefasProvider() if is_fund else BorsapyProvider()
    table = "fund_daily_prices" if is_fund else "stock_daily_bars"
    date_column = "pricing_date" if is_fund else "trading_date"

    try:
        _ensure_schema(engine, asset_type)
        with Session(engine) as session:
            asset = _ensure_asset(session, identifier, asset_type)
            _ensure_mapping(session, asset, provider.name, identifier)
            asset_id = asset.id

            previous_last = session.scalar(
                text(
                    f"SELECT MAX({date_column}) FROM {table} "
                    "WHERE asset_id = :asset_id"
                ),
                {"asset_id": asset_id},
            )
            before_count = session.scalar(
                text(f"SELECT COUNT(*) FROM {table} WHERE asset_id = :asset_id"),
                {"asset_id": asset_id},
            )

            if is_fund:
                result = ingest_fund_incremental(
                    session,
                    provider,
                    asset_id=asset_id,
                    provider_symbol=identifier,
                    as_of=date.today(),
                    bootstrap_days=args.bootstrap_days,
                    overlap_days=args.overlap_days,
                )
            else:
                result = ingest_stock_incremental(
                    session,
                    provider,
                    asset_id=asset_id,
                    provider_symbol=identifier,
                    as_of=date.today(),
                    bootstrap_days=args.bootstrap_days,
                    overlap_days=args.overlap_days,
                )

            after_count = session.scalar(
                text(f"SELECT COUNT(*) FROM {table} WHERE asset_id = :asset_id"),
                {"asset_id": asset_id},
            )
            after_last = session.scalar(
                text(
                    f"SELECT MAX({date_column}) FROM {table} "
                    "WHERE asset_id = :asset_id"
                ),
                {"asset_id": asset_id},
            )
    except Exception as exc:
        print(
            f"INCREMENTAL SMOKE FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    target_label = "Fund code" if is_fund else "Symbol"
    print(f"{target_label}: {identifier}")
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

    if previous_last is None:
        if not result.bootstrap:
            print("INCREMENTAL SMOKE FAILED: expected bootstrap mode", file=sys.stderr)
            return 1
    else:
        if result.bootstrap or result.start_date > previous_last:
            print(
                "INCREMENTAL SMOKE FAILED: incremental window did not resume "
                "from persisted data",
                file=sys.stderr,
            )
            return 1

    if result.ingestion.received == 0 or result.ingestion.written == 0:
        print(
            "INCREMENTAL SMOKE FAILED: provider returned no records for the requested window",
            file=sys.stderr,
        )
        return 1

    if after_last is None or after_last > result.end_date:
        print("INCREMENTAL SMOKE FAILED: invalid persisted upper bound", file=sys.stderr)
        return 1

    print("INCREMENTAL INGESTION SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
