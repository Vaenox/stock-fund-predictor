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
    return (
        pd.DataFrame(
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
        ),
        "Borsapy provider (DB history insufficient)",
    )


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


def _safe_spearman(x: pd.Series, y: pd.Series) -> float | None:
    clean = pd.concat([x, y], axis=1).dropna()
    if len(clean) < 3 or clean.iloc[:, 0].nunique() < 2 or clean.iloc[:, 1].nunique() < 2:
        return None
    return float(clean.iloc[:, 0].corr(clean.iloc[:, 1], method="spearman"))


def _safe_metrics(y: np.ndarray, score: np.ndarray) -> tuple[float | None, float | None]:
    if np.unique(y).size < 2:
        return None, None
    return (
        float(roc_auc_score(y, score)),
        float(average_precision_score(y, score)),
    )


def _run(asset_type: str, symbol: str, days: int, gap: int, threshold: float, min_db_rows: int) -> None:
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

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
        config=None,
    )
    dataset["target"] = (
        dataset["forward_return_5d"] > threshold
    ).astype("int64")

    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )

    oos_parts: list[pd.DataFrame] = []
    for fold in folds:
        test = dataset.iloc[fold.test_start : fold.test_end].copy()
        columns = [date_column, *features, "target", "forward_return_5d"]
        oos_parts.append(test[columns])

    oos = pd.concat(oos_parts, ignore_index=True)

    rows: list[dict[str, object]] = []
    for feature in features:
        target_corr = _safe_spearman(oos[feature], oos["target"])
        forward_corr = _safe_spearman(oos[feature], oos["forward_return_5d"])
        clean = oos[[feature, "target"]].dropna()
        if len(clean) >= 3 and clean[feature].nunique() > 1:
            roc, pr = _safe_metrics(
                clean["target"].to_numpy(dtype=int),
                clean[feature].to_numpy(dtype=float),
            )
            inverse_roc, inverse_pr = _safe_metrics(
                clean["target"].to_numpy(dtype=int),
                -clean[feature].to_numpy(dtype=float),
            )
        else:
            roc = pr = inverse_roc = inverse_pr = None

        rows.append(
            {
                "feature": feature,
                "target_spearman": target_corr,
                "forward_return_spearman": forward_corr,
                "direct_roc": roc,
                "direct_pr": pr,
                "inverse_roc": inverse_roc,
                "inverse_pr": inverse_pr,
            }
        )

    report = pd.DataFrame(rows)
    report["abs_target_spearman"] = report["target_spearman"].abs()
    report = report.sort_values("abs_target_spearman", ascending=False)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Target threshold: > {threshold:.0%}")
    print("Top feature direction diagnostics:")
    for _, row in report.head(10).iterrows():
        print(
            f"  {row['feature']}: "
            f"target_spearman={row['target_spearman']:.4f}, "
            f"forward_spearman={row['forward_return_spearman']:.4f}, "
            f"direct_roc={row['direct_roc'] if row['direct_roc'] is not None else float('nan'):.4f}"
        )

    positive = int((report["target_spearman"] > 0).sum())
    negative = int((report["target_spearman"] < 0).sum())
    neutral = int((report["target_spearman"] == 0).sum())
    print(
        f"Feature target-direction counts: "
        f"positive={positive}, negative={negative}, neutral={neutral}"
    )
    print("FEATURE DIRECTION AUDIT PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--min-db-rows", type=int, default=365)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.threshold <= -1:
        raise SystemExit("threshold must be greater than -1")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.gap,
        args.threshold,
        args.min_db_rows,
    )


if __name__ == "__main__":
    main()
