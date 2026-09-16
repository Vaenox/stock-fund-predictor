from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analysis.features import STOCK_FEATURE_COLUMNS
from app.ml.feature_importance import calculate_gain_importance, fit_model_with_gain_importance
from app.ml.xgboost_baseline import XGBoostBaselineConfig


def _frame(rows: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(19)
    frame = pd.DataFrame(
        rng.normal(size=(rows, len(STOCK_FEATURE_COLUMNS))),
        columns=STOCK_FEATURE_COLUMNS,
    )
    frame["target"] = pd.Series(np.arange(rows) % 4 == 0, dtype="Int64")
    return frame


def test_gain_importance_returns_all_stock_features():
    model, rows = fit_model_with_gain_importance(
        _frame(),
        asset_type="stock",
        config=XGBoostBaselineConfig(n_estimators=10),
    )

    assert model is not None
    assert [row.feature for row in rows] == sorted(STOCK_FEATURE_COLUMNS, key=lambda value: (-dict((r.feature, r.importance) for r in rows)[value], value))
    assert {row.feature for row in rows} == set(STOCK_FEATURE_COLUMNS)
    assert all(np.isfinite(row.importance) and row.importance >= 0.0 for row in rows)


def test_gain_importance_rejects_single_class_target():
    frame = _frame()
    frame["target"] = 0

    with pytest.raises(ValueError, match="only one class"):
        fit_model_with_gain_importance(frame, asset_type="stock")


def test_calculate_gain_importance_zero_fills_missing_booster_features():
    model, _ = fit_model_with_gain_importance(
        _frame(),
        asset_type="stock",
        config=XGBoostBaselineConfig(n_estimators=10),
    )

    rows = calculate_gain_importance(model, asset_type="stock")
    assert len(rows) == len(STOCK_FEATURE_COLUMNS)
    assert {row.feature for row in rows} == set(STOCK_FEATURE_COLUMNS)
