from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


AssetType = Literal["stock", "fund"]

STOCK_FEATURE_COLUMNS = (
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_mid",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "bb_position",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "return_1d",
    "return_5d",
    "volatility_20",
    "atr_14",
    "atr_pct_14",
    "adx_14",
    "volume_sma_20",
    "volume_ratio_20",
    "volume_change_1d",
)

FUND_FEATURE_COLUMNS = (
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_20",
    "ema_50",
    "ema_200",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_mid",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "bb_position",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "return_1d",
    "return_5d",
    "volatility_20",
)


@dataclass(frozen=True, slots=True)
class MLFeatureConfig:
    """Canonical configuration for the first supervised-learning dataset."""

    horizon: int = 5
    positive_return_threshold: float = 0.03
    drop_incomplete_features: bool = True

    def __post_init__(self) -> None:
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")
        if self.positive_return_threshold <= -1.0:
            raise ValueError("positive_return_threshold must be greater than -1")


def feature_columns(asset_type: AssetType) -> tuple[str, ...]:
    if asset_type == "stock":
        return STOCK_FEATURE_COLUMNS
    if asset_type == "fund":
        return FUND_FEATURE_COLUMNS
    raise ValueError(f"unsupported asset_type: {asset_type}")


def _date_column(asset_type: AssetType) -> str:
    return "trading_date" if asset_type == "stock" else "pricing_date"


def _price_column(asset_type: AssetType) -> str:
    return "close" if asset_type == "stock" else "unit_price"


def _validate_input(frame: pd.DataFrame, asset_type: AssetType) -> None:
    date_column = _date_column(asset_type)
    price_column = _price_column(asset_type)
    required = (date_column, price_column)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    missing_features = [
        column for column in feature_columns(asset_type) if column not in frame.columns
    ]
    if missing_features:
        raise ValueError(
            "missing required feature columns: " + ", ".join(missing_features)
        )


def build_ml_feature_dataset(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    config: MLFeatureConfig | None = None,
) -> pd.DataFrame:
    """Build a time-ordered supervised-learning dataset without feature leakage.

    The selected feature columns are calculated upstream by the indicator engine.
    The training-only label is defined as the return from the current observation
    to the next ``horizon`` available observations. Rows without a complete
    feature vector or without a full future horizon are excluded by default.
    """
    config = config or MLFeatureConfig()
    _validate_input(frame, asset_type)

    date_column = _date_column(asset_type)
    price_column = _price_column(asset_type)
    columns = feature_columns(asset_type)

    result = frame.sort_values(date_column).reset_index(drop=True).copy()
    result[price_column] = pd.to_numeric(result[price_column], errors="raise")

    future_price = result[price_column].shift(-config.horizon)
    result["forward_return_5d"] = future_price / result[price_column] - 1.0
    result["target"] = (
        result["forward_return_5d"] > config.positive_return_threshold
    ).astype("Int64")

    selected_columns = [date_column, price_column, *columns]
    result = result[selected_columns + ["forward_return_5d", "target"]]

    if config.drop_incomplete_features:
        result = result.dropna(subset=list(columns)).copy()

    result = result.dropna(subset=["forward_return_5d"]).reset_index(drop=True)
    return result


def build_inference_features(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    drop_incomplete_features: bool = True,
) -> pd.DataFrame:
    """Return only causal model features for live/inference use.

    No future-return or target columns are produced by this function.
    """
    _validate_input(frame, asset_type)

    date_column = _date_column(asset_type)
    price_column = _price_column(asset_type)
    columns = feature_columns(asset_type)

    result = frame.sort_values(date_column).reset_index(drop=True).copy()
    selected = result[[date_column, price_column, *columns]]
    if drop_incomplete_features:
        selected = selected.dropna(subset=list(columns))
    return selected.reset_index(drop=True).copy()
