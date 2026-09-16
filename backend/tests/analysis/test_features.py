from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analysis.features import (
    FUND_FEATURE_COLUMNS,
    STOCK_FEATURE_COLUMNS,
    MLFeatureConfig,
    build_inference_features,
    build_ml_feature_dataset,
)
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators


def _stock_frame(rows: int = 260) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series(100 + np.arange(rows) * 0.5, dtype=float)
    return pd.DataFrame(
        {
            "trading_date": dates,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.linspace(10_000, 20_000, rows),
        }
    )


def _fund_frame(rows: int = 260) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    unit_price = pd.Series(10 + np.arange(rows) * 0.02, dtype=float)
    return pd.DataFrame({"pricing_date": dates, "unit_price": unit_price})


def test_stock_feature_dataset_drops_warmup_and_futureless_rows():
    indicators = calculate_stock_indicators(_stock_frame())
    result = build_ml_feature_dataset(indicators, asset_type="stock")

    assert len(result) == 260 - 199 - 5
    assert list(result.columns) == [
        "trading_date",
        "close",
        *STOCK_FEATURE_COLUMNS,
        "forward_return_5d",
        "target",
    ]
    assert result[STOCK_FEATURE_COLUMNS].notna().all().all()
    assert result["forward_return_5d"].notna().all()
    assert result["target"].isin([0, 1]).all()


def test_fund_feature_dataset_uses_available_observation_horizon():
    indicators = calculate_fund_indicators(_fund_frame())
    result = build_ml_feature_dataset(indicators, asset_type="fund")

    assert len(result) == 260 - 199 - 5
    assert result[FUND_FEATURE_COLUMNS].notna().all().all()
    assert result["target"].isin([0, 1]).all()


def test_target_is_based_on_next_five_observations():
    indicators = calculate_stock_indicators(_stock_frame())
    result = build_ml_feature_dataset(
        indicators,
        asset_type="stock",
        config=MLFeatureConfig(horizon=5, positive_return_threshold=0.0),
    )

    expected = result.loc[0, "close"]
    future = indicators.loc[204, "close"]
    assert result.loc[0, "forward_return_5d"] == pytest.approx(future / expected - 1.0)
    assert result.loc[0, "target"] == 1


def test_inference_features_do_not_expose_training_target():
    indicators = calculate_stock_indicators(_stock_frame())
    result = build_inference_features(indicators, asset_type="stock")

    assert "forward_return_5d" not in result.columns
    assert "target" not in result.columns
    assert list(result.columns) == ["trading_date", "close", *STOCK_FEATURE_COLUMNS]


def test_feature_builder_does_not_use_future_feature_rows():
    full = calculate_stock_indicators(_stock_frame())
    truncated = calculate_stock_indicators(_stock_frame().iloc[:230].copy())

    full_features = build_inference_features(full, asset_type="stock")
    truncated_features = build_inference_features(truncated, asset_type="stock")

    anchor_date = full_features.loc[0, "trading_date"]
    full_row = full_features[full_features["trading_date"] == anchor_date].iloc[0]
    truncated_row = truncated_features[truncated_features["trading_date"] == anchor_date].iloc[0]

    for column in STOCK_FEATURE_COLUMNS:
        assert full_row[column] == pytest.approx(truncated_row[column])


def test_missing_feature_column_is_rejected():
    indicators = calculate_stock_indicators(_stock_frame()).drop(columns=["ema_200"])

    with pytest.raises(ValueError, match="missing required feature columns"):
        build_ml_feature_dataset(indicators, asset_type="stock")
