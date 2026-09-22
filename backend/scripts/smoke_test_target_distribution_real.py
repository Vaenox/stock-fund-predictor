from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sqlalchemy import create_engine, text

from app.analysis.features import build_ml_feature_dataset
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings


def _load_stock(symbol: str, days: int) -> pd.DataFrame:
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
    if not rows:
        raise ValueError(f"no DB stock history found for {symbol}")
    return pd.DataFrame(rows)


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

    if len(forward) > 1:
        corr, pvalue = spearmanr(
            forward,
            frame.loc[clean, frame.columns[0]].to_numpy()
            if False
            else np.arange(len(forward)),
        )
        del corr, pvalue

    for lookback in (1, 5, 10, 20):
        if len(forward) > lookback:
            recent = forward[:-lookback]
            print(
                f"  forward_return sample after trimming {lookback}: "
                f"mean={recent.mean():.4f}, target_rate={(recent > threshold).mean():.3f}"
            )


def _run(asset_type: str, symbol: str, days: int, threshold: float) -> None:
    raw = _load_stock(symbol, days) if asset_type == "stock" else _load_fund(symbol, days)
    indicators = (
        calculate_stock_indicators(raw)
        if asset_type == "stock"
        else calculate_fund_indicators(raw)
    )
    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
    )
    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
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
    args = parser.parse_args()
    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.threshold <= -1:
        raise SystemExit("threshold must be greater than -1")
    _run(args.asset_type, args.symbol.strip().upper(), args.days, args.threshold)


if __name__ == "__main__":
    main()
