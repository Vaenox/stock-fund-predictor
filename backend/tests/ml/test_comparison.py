from __future__ import annotations

import numpy as np
import pandas as pd

from app.analysis.features import STOCK_FEATURE_COLUMNS
from app.ml.comparison import compare_baseline_vs_tuned


def _frame(rows: int = 140) -> pd.DataFrame:
    rng = np.random.default_rng(21)
    frame = pd.DataFrame(rng.normal(size=(rows, len(STOCK_FEATURE_COLUMNS))), columns=STOCK_FEATURE_COLUMNS)
    frame["target"] = pd.Series(np.arange(rows) % 4 == 0, dtype="Int64")
    return frame


def test_baseline_vs_tuned_uses_same_outer_folds_and_gap():
    results = compare_baseline_vs_tuned(
        _frame(),
        asset_type="stock",
        n_splits=2,
        test_size=20,
        gap=5,
    )

    assert len(results) == 2
    assert all(result.test_start - result.train_end == 5 for result in results)
    assert all(result.baseline.test_start == result.test_start for result in results)
    assert all(result.baseline.test_end == result.test_end for result in results)
    assert all(result.tuned_config.random_state == 42 for result in results)
