from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from app.analysis.features import build_inference_features, build_ml_feature_dataset
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators


def _stock_frame(days: int) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=days, freq="D")
    close = pd.Series(100 + np.arange(days) * 0.25, dtype=float)
    return pd.DataFrame(
        {
            "trading_date": dates,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.linspace(10_000, 30_000, days),
        }
    )


def _fund_frame(days: int) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=days, freq="D")
    unit_price = pd.Series(10 + np.arange(days) * 0.01, dtype=float)
    return pd.DataFrame({"pricing_date": dates, "unit_price": unit_price})


def _run(asset_type: str, days: int) -> None:
    raw = _stock_frame(days) if asset_type == "stock" else _fund_frame(days)
    indicators = (
        calculate_stock_indicators(raw)
        if asset_type == "stock"
        else calculate_fund_indicators(raw)
    )

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    inference = build_inference_features(indicators, asset_type=asset_type)

    date_column = "trading_date" if asset_type == "stock" else "pricing_date"
    print(f"Asset type: {asset_type}")
    print(f"Raw rows: {len(raw)}")
    print(f"Training rows: {len(dataset)}")
    print(f"Inference rows: {len(inference)}")
    print(f"Date window: {inference[date_column].iloc[0]}->{inference[date_column].iloc[-1]}")
    print(f"Target distribution: {dataset['target'].value_counts().to_dict()}")

    assert dataset["target"].isin([0, 1]).all()
    assert dataset["forward_return_5d"].notna().all()
    assert "target" not in inference.columns
    assert "forward_return_5d" not in inference.columns

    anchor_date = inference[date_column].iloc[0]
    truncated = indicators.iloc[:-20].copy()
    truncated_inference = build_inference_features(
        truncated,
        asset_type=asset_type,
    )
    full_row = inference[inference[date_column] == anchor_date].iloc[0]
    truncated_row = truncated_inference[truncated_inference[date_column] == anchor_date].iloc[0]
    feature_columns = [column for column in inference.columns if column not in {date_column, "close", "unit_price"}]
    for column in feature_columns:
        assert full_row[column] == truncated_row[column], f"future leakage detected in {column}"

    print("LOOK-AHEAD CHECK: PASSED")
    print("ML FEATURE SMOKE TEST PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), default="stock")
    parser.add_argument("--days", type=int, default=260)
    args = parser.parse_args()
    if args.days < 205:
        raise SystemExit("days must be at least 205")
    _run(args.asset_type, args.days)


if __name__ == "__main__":
    main()
