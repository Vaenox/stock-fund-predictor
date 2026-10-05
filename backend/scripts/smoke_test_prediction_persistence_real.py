from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data import record_prediction, get_latest_prediction
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.models.market_data import Asset, AssetType
from app.services.prediction import generate_latest_prediction


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame(
        {
            "trading_date": [r.trading_date for r in records],
            "open": [float(r.open) for r in records],
            "high": [float(r.high) for r in records],
            "low": [float(r.low) for r in records],
            "close": [float(r.close) for r in records],
            "volume": [
                float(r.volume) if r.volume is not None else float("nan")
                for r in records
            ],
        }
    )


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = []
    chunks = tuple(
        provider._chunks(
            start_date,
            end_date,
            provider._settings.max_days_per_request,
        )
    )
    for index, (chunk_start, chunk_end) in enumerate(chunks):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
        if index < len(chunks) - 1 and chunk_delay > 0:
            time.sleep(chunk_delay)

    return (
        pd.DataFrame(
            {
                "pricing_date": [r.pricing_date for r in records],
                "unit_price": [float(r.unit_price) for r in records],
            }
        )
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )


def _find_asset(session: Session, symbol: str, asset_type: str) -> Asset:
    expected_type = (
        AssetType.STOCK if asset_type == "stock" else AssetType.FUND
    )
    statement = select(Asset).where(
        Asset.canonical_symbol == symbol.strip().upper(),
        Asset.asset_type == expected_type,
    )
    asset = session.scalar(statement)
    if asset is None:
        raise ValueError(
            f"Asset not found in canonical universe: {symbol.strip().upper()} ({asset_type})"
        )
    return asset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and persist one current prediction."
    )
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    symbol = args.symbol.strip().upper()
    if args.asset_type == "stock":
        raw = _stock_frame(symbol, args.days)
        provider = "borsapy"
    else:
        raw = _fund_frame(symbol, args.days, args.chunk_delay)
        provider = "tefas"

    engine = create_engine(get_settings().database_url, future=True)
    with Session(engine) as session:
        asset = _find_asset(session, symbol, args.asset_type)
        result = generate_latest_prediction(
            asset_id=asset.id,
            asset_type=args.asset_type,
            raw_frame=raw,
            source_provider=provider,
            quality_ok=True,
            stale_days=0,
            gap=args.gap,
        )
        record = record_prediction(session, result.payload)
        latest = get_latest_prediction(session, asset_id=asset.id)

        if latest is None or latest.id != record.id:
            raise RuntimeError("persisted prediction could not be read back")

        print(f"Asset type: {args.asset_type}")
        print(f"Symbol: {symbol}")
        print(f"Asset ID: {asset.id}")
        print(f"Raw rows: {result.raw_rows}")
        print(f"Training rows: {result.training_rows}")
        print(f"Prediction date: {result.payload.prediction_date}")
        print(f"Data as of: {result.payload.data_as_of}")
        print(f"Model version: {result.model_version}")
        print(f"Inner PR-AUC: {result.inner_pr_auc:.6f}")
        print(f"ML probability: {result.payload.ml_probability}")
        print(f"Technical score: {result.payload.technical_score}")
        print(f"Risk score: {result.payload.risk_score}")
        print(f"Risk adjustment: {result.payload.risk_adjustment}")
        print(f"Signal score: {result.payload.signal_score}")
        print(f"Target weight: {result.payload.target_weight}")
        print(f"Persisted prediction ID: {record.id}")
        print("REAL PREDICTION PERSISTENCE SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
