from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import pandas as pd

from app.analysis.features import build_ml_feature_dataset
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.xgboost_baseline import XGBoostBaselineConfig, evaluate_walk_forward


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame(
        {
            "trading_date": [record.trading_date for record in records],
            "open": [float(record.open) for record in records],
            "high": [float(record.high) for record in records],
            "low": [float(record.low) for record in records],
            "close": [float(record.close) for record in records],
            "volume": [float(record.volume) if record.volume is not None else float("nan") for record in records],
        }
    )


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = []
    for chunk_start, chunk_end in provider._chunks(start_date, end_date, provider._settings.max_days_per_request):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
        if chunk_end < end_date and chunk_delay > 0:
            time.sleep(chunk_delay)
    return pd.DataFrame(
        {
            "pricing_date": [record.pricing_date for record in records],
            "unit_price": [float(record.unit_price) for record in records],
        }
    ).drop_duplicates(subset=["pricing_date"]).sort_values("pricing_date").reset_index(drop=True)


def _run(asset_type: str, symbol: str, days: int, n_splits: int, test_size: int, gap: int, chunk_delay: float) -> None:
    if asset_type == "stock":
        raw = _stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
    else:
        raw = _fund_frame(symbol, days, chunk_delay)
        indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    metrics = evaluate_walk_forward(
        dataset,
        asset_type=asset_type,
        n_splits=n_splits,
        test_size=test_size,
        gap=gap,
        config=XGBoostBaselineConfig(),
    )

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol}")
    print(f"Raw rows: {len(raw)}")
    print(f"Training rows: {len(dataset)}")
    print(f"Target distribution: {dataset['target'].value_counts().sort_index().to_dict()}")
    for metric in metrics:
        print(
            f"Fold {metric.fold}: train_end={metric.train_end} test={metric.test_start}->{metric.test_end} "
            f"train_target={{0: {metric.train_negative_count}, 1: {metric.train_positive_count}}} "
            f"test_target={{0: {metric.test_negative_count}, 1: {metric.test_positive_count}}} "
            f"ROC-AUC={metric.roc_auc} PR-AUC={metric.pr_auc} "
            f"accuracy={metric.accuracy:.4f} precision={metric.precision:.4f} recall={metric.recall:.4f} "
            f"positive_rate={metric.positive_rate:.4f}"
        )

    assert metrics
    assert all(metric.test_start - metric.train_end == gap for metric in metrics)
    assert all(metric.train_negative_count > 0 and metric.train_positive_count > 0 for metric in metrics)
    assert all(0.0 <= metric.accuracy <= 1.0 for metric in metrics)
    assert all(0.0 <= metric.precision <= 1.0 for metric in metrics)
    assert all(0.0 <= metric.recall <= 1.0 for metric in metrics)
    print("REAL XGBOOST BASELINE SMOKE TEST PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), default="stock")
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument("--test-size", type=int, default=40)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--chunk-delay", type=float, default=10.0)
    args = parser.parse_args()
    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.test_size <= 0:
        raise SystemExit("test-size must be positive")
    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.n_splits,
        args.test_size,
        args.gap,
        args.chunk_delay,
    )


if __name__ == "__main__":
    main()
