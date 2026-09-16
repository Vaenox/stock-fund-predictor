from __future__ import annotations

import numpy as np
import pandas as pd

from app.analysis.features import STOCK_FEATURE_COLUMNS
from app.ml.xgboost_baseline import XGBoostBaselineConfig, evaluate_walk_forward, fit_baseline_model


def _frame(rows: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        rng.normal(size=(rows, len(STOCK_FEATURE_COLUMNS))),
        columns=STOCK_FEATURE_COLUMNS,
    )
    frame["target"] = pd.Series(np.arange(rows) % 4 == 0, dtype="Int64")
    frame["forward_return_5d"] = frame["target"].astype(float) * 0.04 - 0.01
    return frame


def test_phase4_acceptance_fit_predict_probability_contract():
    frame = _frame()
    model = fit_baseline_model(
        frame,
        asset_type="stock",
        config=XGBoostBaselineConfig(n_estimators=10),
    )

    probability = model.predict_proba(frame[list(STOCK_FEATURE_COLUMNS)])[:, 1]

    assert probability.shape == (len(frame),)
    assert np.isfinite(probability).all()
    assert np.all((probability >= 0.0) & (probability <= 1.0))


def test_phase4_acceptance_walk_forward_respects_five_observation_gap():
    metrics = evaluate_walk_forward(
        _frame(),
        asset_type="stock",
        n_splits=2,
        test_size=15,
        gap=5,
        config=XGBoostBaselineConfig(n_estimators=10),
    )

    assert len(metrics) == 2
    assert all(metric.test_start - metric.train_end == 5 for metric in metrics)
    assert all(metric.train_negative_count > 0 for metric in metrics)
    assert all(metric.train_positive_count > 0 for metric in metrics)


def test_phase4_acceptance_single_class_test_fold_is_reported_not_scored():
    frame = _frame(80)
    frame.loc[65:, "target"] = 0

    metrics = evaluate_walk_forward(
        frame,
        asset_type="stock",
        n_splits=1,
        test_size=10,
        gap=5,
        config=XGBoostBaselineConfig(n_estimators=10),
    )

    metric = metrics[0]
    assert metric.test_positive_count == 0
    assert metric.roc_auc is None
    assert metric.pr_auc is None
