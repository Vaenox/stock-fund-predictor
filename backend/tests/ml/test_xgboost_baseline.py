from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analysis.features import STOCK_FEATURE_COLUMNS
from app.ml.xgboost_baseline import (
    XGBoostBaselineConfig,
    evaluate_walk_forward,
    fit_baseline_model,
)


def _training_frame(rows: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(rng.normal(size=(rows, len(STOCK_FEATURE_COLUMNS))), columns=STOCK_FEATURE_COLUMNS)
    frame["target"] = pd.Series(np.arange(rows) % 3 == 0, dtype="Int64")
    frame["forward_return_5d"] = frame["target"].astype(float) * 0.05 - 0.01
    return frame


def test_fit_baseline_model_returns_classifier():
    model = fit_baseline_model(_training_frame(), asset_type="stock")

    probabilities = model.predict_proba(_training_frame()[list(STOCK_FEATURE_COLUMNS)])[:, 1]
    assert len(probabilities) == 120
    assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_training_rejects_missing_feature_values():
    frame = _training_frame()
    frame.loc[0, STOCK_FEATURE_COLUMNS[0]] = np.nan

    with pytest.raises(ValueError, match="missing values"):
        fit_baseline_model(frame, asset_type="stock")


def test_walk_forward_evaluation_returns_fold_metrics_and_class_counts():
    metrics = evaluate_walk_forward(
        _training_frame(),
        asset_type="stock",
        n_splits=3,
        test_size=20,
        gap=5,
        config=XGBoostBaselineConfig(n_estimators=20),
    )

    assert len(metrics) == 3
    assert all(metric.test_start - metric.train_end == 5 for metric in metrics)
    assert all(metric.train_negative_count > 0 for metric in metrics)
    assert all(metric.train_positive_count > 0 for metric in metrics)
    assert all(metric.test_negative_count + metric.test_positive_count == 20 for metric in metrics)
    assert all(0.0 <= metric.accuracy <= 1.0 for metric in metrics)


def test_walk_forward_requires_target_horizon_gap():
    with pytest.raises(ValueError, match="at least the 5-observation"):
        evaluate_walk_forward(_training_frame(), asset_type="stock", gap=4)
