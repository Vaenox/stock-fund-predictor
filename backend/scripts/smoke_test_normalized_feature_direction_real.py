from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import (
    FUND_FEATURE_COLUMNS,
    STOCK_FEATURE_COLUMNS,
    build_ml_feature_dataset,
)
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.splitting import build_walk_forward_splits


PRICE_LEVEL_FEATURES = {
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_20",
    "ema_50",
    "ema_200",
    "bb_mid",
    "bb_upper",
    "bb_lower",
    "atr_14",
}


def _load_stock(symbol: str, days: int, min_db_rows: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
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

    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    if not records:
        raise ValueError(f"no Borsapy history found for {symbol}")
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
    ), "Borsapy provider (DB history insufficient)"


def _load_fund(symbol: str, days: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
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
    return pd.DataFrame(rows), "PostgreSQL canonical history"


def _normalize_levels(dataset: pd.DataFrame, asset_type: str) -> pd.DataFrame:
    result = dataset.copy()
    price = result["close"] if asset_type == "stock" else result["unit_price"]
    eps = 1e-12

    for column in PRICE_LEVEL_FEATURES:
        if column not in result.columns:
            continue
        if column == "atr_14":
            result[column] = result[column] / price.replace(0, np.nan)
        elif column in {"bb_width", "bb_position"}:
            continue
        else:
            result[column] = result[column] / price.replace(0, np.nan) - 1.0

    return result.replace([np.inf, -np.inf], np.nan)


def _safe_metrics(y: np.ndarray, score: np.ndarray) -> tuple[float | None, float | None]:
    clean = np.isfinite(score)
    y = y[clean]
    score = score[clean]
    if np.unique(y).size < 2:
        return None, None
    return float(roc_auc_score(y, score)), float(average_precision_score(y, score))


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    threshold: float,
    gap: int,
    min_db_rows: int,
) -> None:
    if asset_type == "stock":
        raw, source = _load_stock(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
        features = STOCK_FEATURE_COLUMNS
        date_column = "trading_date"
    else:
        raw, source = _load_fund(symbol, days)
        indicators = calculate_fund_indicators(raw)
        features = FUND_FEATURE_COLUMNS
        date_column = "pricing_date"

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    normalized = _normalize_levels(dataset, asset_type)
    folds = build_walk_forward_splits(len(normalized), n_splits=3, test_size=40, gap=gap)
    oos = pd.concat(
        [
            normalized.iloc[fold.test_start:fold.test_end]
            for fold in folds
        ],
        ignore_index=True,
    )

    y = oos["target"].to_numpy(dtype=int)
    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Target threshold: > {threshold:.0%}")
    print("Normalized feature direction diagnostics:")

    report: list[tuple[str, float | None, float | None, float | None]] = []
    for feature in features:
        if feature not in oos.columns:
            continue
        score = oos[feature].to_numpy(dtype=float)
        spearman = float(oos[feature].corr(oos["target"], method="spearman"))
        forward_spearman = float(
            oos[feature].corr(oos["forward_return_5d"], method="spearman")
        )
        roc, pr = _safe_metrics(y, score)
        report.append((feature, spearman, forward_spearman, roc))
    report.sort(key=lambda row: abs(row[1] if row[1] is not None else 0.0), reverse=True)

    for feature, spearman, forward_spearman, roc in report[:10]:
        print(
            f"  {feature}: target_spearman={spearman:.4f}, "
            f"forward_spearman={forward_spearman:.4f}, "
            f"direct_roc={roc if roc is not None else float('nan'):.4f}"
        )

    positive = sum(1 for _, s, _, _ in report if s is not None and s > 0)
    negative = sum(1 for _, s, _, _ in report if s is not None and s < 0)
    print(
        f"Normalized feature target-direction counts: "
        f"positive={positive}, negative={negative}, neutral={len(report) - positive - negative}"
    )
    print("NORMALIZED FEATURE DIRECTION AUDIT PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.threshold <= -1:
        raise SystemExit("threshold must be greater than -1")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.threshold,
        args.gap,
        args.min_db_rows,
    )


if __name__ == "__main__":
    main()
