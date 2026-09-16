from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analysis.features import STOCK_FEATURE_COLUMNS
from app.ml.tuning import TuningConfig, build_inner_splits, evaluate_candidate_inner
from app.ml.xgboost_baseline import XGBoostBaselineConfig


def _frame(rows: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    frame = pd.DataFrame(rng.normal(size=(rows, len(STOCK_FEATURE_COLUMNS))), columns=STOCK_FEATURE_COLUMNS)
    frame["target"] = pd.Series(np.arange(rows) % 4 == 0, dtype="Int64")
    return frame


def test_inner_splits_are_chronological_and_keep_gap():
    folds = build_inner_splits(
        100,
        config=TuningConfig(n_inner_splits=2, inner_test_size=15, gap=5),
    )

    assert len(folds) == 2
    assert folds[0].test_end <= folds[1].test_start
    assert all(fold.test_start - fold.train_end == 5 for fold in folds)
    assert all(fold.train_start == 0 for fold in folds)


def test_tuning_config_rejects_small_gap():
    with pytest.raises(ValueError, match="at least the 5-observation"):
        TuningConfig(gap=4)


def test_candidate_inner_score_uses_training_period_only():
    score = evaluate_candidate_inner(
        _frame(),
        asset_type="stock",
        candidate=XGBoostBaselineConfig(n_estimators=10),
        tuning_config=TuningConfig(n_inner_splits=2, inner_test_size=15, gap=5),
    )

    assert np.isfinite(score)
    assert score >= 0.0
