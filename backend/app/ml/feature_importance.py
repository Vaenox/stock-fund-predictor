from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.analysis.features import AssetType, feature_columns
from app.ml.xgboost_baseline import build_model


@dataclass(frozen=True, slots=True)
class FeatureImportanceRow:
    feature: str
    importance: float


def calculate_gain_importance(model, *, asset_type: AssetType) -> tuple[FeatureImportanceRow, ...]:
    columns = list(feature_columns(asset_type))
    score_by_name = model.get_booster().get_score(importance_type="gain")
    values = [FeatureImportanceRow(feature=feature, importance=float(score_by_name.get(feature, 0.0))) for feature in columns]
    return tuple(sorted(values, key=lambda item: (-item.importance, item.feature)))


def fit_model_with_gain_importance(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    config=None,
):
    columns = list(feature_columns(asset_type))
    required = [*columns, "target"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("missing required importance columns: " + ", ".join(missing))
    if frame[columns].isna().any().any() or frame["target"].isna().any():
        raise ValueError("feature importance training data contains missing values")
    if frame["target"].nunique() < 2:
        raise ValueError("feature importance training target contains only one class")

    model = build_model(config)
    model.fit(frame[columns], frame["target"].astype(int))
    return model, calculate_gain_importance(model, asset_type=asset_type)
