from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from app.analysis.features import build_ml_feature_dataset
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider


def _load_stock_provider(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    if not records:
        raise ValueError(f"no Borsapy history found for {symbol}")
    return pd.DataFrame(
        {
            "trading_date": [record.trading_date for record in records],
            "open": [float(record.open) for record in records],
            "high": [float(record.high) for record in records],
            "low": [float(record.low) for record in records],
            "close": [float(record.close) for record in records],
            "volume": [
                float(record.volume) if record.volume is not None else float("nan")
                for record in records
            ],
        }
    )


def _load_stock(symbol: str, days: int, min_db_rows: int) -> tuple[pd.DataFrame, str]:
    engine = create_engine(get_settings().database_url, future=True)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT b.trading_date, b.open, b.high, b.low, b.close, b.volume
                FROM stock_daily_bars b
                JOIN assets a ON a.id = b.asset_id
                WHERE a.canonical_symbol = :symbol
                  AND b.trading_date BETWEEN :start_date AND :end_date
                ORDER BY b.trading_date
                """
            ),
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

    if len(rows) >= min_db_rows:
        return pd.DataFrame(rows), "PostgreSQL canonical history"

    return _load_stock_provider(symbol, days), "Borsapy provider (DB history insufficient)"


def _load_fund(symbol: str, days: int) -> pd.DataFrame:
    engine = create_engine(get_settings().database_url, future=True)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT p.pricing_date, p.unit_price
                FROM fund_daily_prices p
                JOIN assets a ON a.id = p.asset_id
                WHERE a.canonical_symbol = :symbol
                  AND p.pricing_date BETWEEN :start_date AND :end_date
                ORDER BY p.pricing_date
                """
            ),
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()
    if not rows:
        raise ValueError(f"no DB fund history found for {symbol}")
    return pd.DataFrame(rows)


def _metrics(frame: pd.DataFrame, threshold: float) -> None:
    forward = frame["forward_return_5d"].to_numpy(dtype=float)
    clean = np.isfinite(forward)
    forward = forward[clean]

    if len(forward) == 0:
        raise ValueError("no finite forward_return_5d observations available")

    thresholds = (0.00, 0.01, 0.02, 0.03, 0.05, 0.10)
    print("Forward-return distribution:")
    print(f"  count={len(forward)}")
    print(f"  mean={np.mean(forward):.4f}")
    print(f"  std={np.std(forward):.4f}")
    print(
        "  quantiles="
        + ", ".join(
            f"p{q}={np.quantile(forward, q / 100):.4f}"
            for q in (1, 5, 25, 50, 75, 95, 99)
        )
    )

    for t in thresholds:
        mask = forward > t
        print(
            f"  return > {t:.0%}: "
            f"count={int(mask.sum())}, rate={mask.mean():.3f}"
        )

    positive = forward > threshold
    negative_or_equal = forward <= threshold
    print(f"Canonical target threshold: > {threshold:.2%}")
    print(
        f"  positive={int(positive.sum())} ({positive.mean():.3f}), "
        f"non_positive={int(negative_or_equal.sum())} ({negative_or_equal.mean():.3f})"
    )

    print("Recent target-rate snapshot:")
    window = min(120, len(forward))
    if len(forward) >= window:
        recent = forward[-window:]
        print(
            f"  latest_{window}: mean={recent.mean():.4f}, "
            f"target_rate={(recent > threshold).mean():.3f}"
        )

    

def _run(
    asset_type: str,
    symbol: str,
    days: int,
    threshold: float,
    min_db_rows: int,
) -> None:
    if asset_type == "stock":
        raw, source = _load_stock(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
    else:
        raw = _load_fund(symbol, days)
        source = "PostgreSQL canonical history"
        indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
    )
    if dataset.empty:
        raise ValueError(
            "ML feature dataset is empty; insufficient historical observations "
            "after indicator warm-up."
        )

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Dataset rows: {len(dataset)}")
    print(
        f"Dataset range: "
        f"{dataset.iloc[0, 0]} -> {dataset.iloc[-1, 0]}"
    )
    _metrics(dataset, threshold)
    print("TARGET DISTRIBUTION DIAGNOSTIC PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--min-db-rows", type=int, default=365)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.threshold <= -1:
        raise SystemExit("threshold must be greater than -1")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.threshold,
        args.min_db_rows,
    )


if __name__ == "__main__":
    main()
