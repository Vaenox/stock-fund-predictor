from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import pandas as pd

from app.analysis.features import build_ml_feature_dataset
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.feature_importance import fit_model_with_gain_importance
from app.ml.tuning import TuningConfig, select_best_candidate


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame({
        "trading_date": [r.trading_date for r in records],
        "open": [float(r.open) for r in records],
        "high": [float(r.high) for r in records],
        "low": [float(r.low) for r in records],
        "close": [float(r.close) for r in records],
        "volume": [float(r.volume) if r.volume is not None else float("nan") for r in records],
    })


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = []
    for chunk_start, chunk_end in provider._chunks(start_date, end_date, provider._settings.max_days_per_request):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
        if chunk_end < end_date and chunk_delay > 0:
            time.sleep(chunk_delay)
    return (
        pd.DataFrame({
            "pricing_date": [r.pricing_date for r in records],
            "unit_price": [float(r.unit_price) for r in records],
        })
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )


def _run(asset_type: str, symbol: str, days: int, inner_splits: int, inner_test_size: int, gap: int, chunk_delay: float, tuned: bool) -> None:
    if asset_type == "stock":
        raw = _stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
    else:
        raw = _fund_frame(symbol, days, chunk_delay)
        indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)

    config = None
    if tuned:
        selected = select_best_candidate(
            dataset,
            asset_type=asset_type,
            tuning_config=TuningConfig(
                n_inner_splits=inner_splits,
                inner_test_size=inner_test_size,
                gap=gap,
            ),
        )
        config = selected.config
        print(f"Selected tuned config: {config}")
        print(f"Inner PR-AUC: {selected.score:.6f}")

    model, importance = fit_model_with_gain_importance(
        dataset,
        asset_type=asset_type,
        config=config,
    )

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol}")
    print(f"Raw rows: {len(raw)}")
    print(f"Training rows: {len(dataset)}")
    print(f"Model: {'tuned' if tuned else 'baseline'}")
    print("Top feature importances (gain):")
    for row in importance[:10]:
        print(f"  {row.feature}: {row.importance:.6f}")
    assert importance
    assert all(row.importance >= 0.0 for row in importance)
    print("REAL XGBOOST FEATURE IMPORTANCE SMOKE TEST PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), default="stock")
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--inner-splits", type=int, default=2)
    parser.add_argument("--inner-test-size", type=int, default=20)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--chunk-delay", type=float, default=0.0)
    parser.add_argument("--tuned", action="store_true")
    args = parser.parse_args()
    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.inner_test_size <= 0:
        raise SystemExit("inner-test-size must be positive")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.inner_splits,
        args.inner_test_size,
        args.gap,
        args.chunk_delay,
        args.tuned,
    )


if __name__ == "__main__":
    main()
