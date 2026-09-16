from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, precision_score, recall_score, roc_auc_score

from app.analysis.features import AssetType, feature_columns
from app.ml.splitting import TimeSeriesFold, build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import FoldMetrics, XGBoostBaselineConfig, build_model


@dataclass(frozen=True, slots=True)
class ModelComparison:
    fold: int
    train_end: int
    test_start: int
    test_end: int
    baseline: FoldMetrics
    tuned_config: XGBoostBaselineConfig
    tuned_roc_auc: float | None
    tuned_pr_auc: float | None
    tuned_accuracy: float
    tuned_precision: float
    tuned_recall: float


def _safe_roc_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(roc_auc_score(y_true, probability))


def _safe_pr_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(average_precision_score(y_true, probability))


def compare_baseline_vs_tuned(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    n_splits: int = 3,
    test_size: int = 40,
    gap: int = 5,
    baseline_config: XGBoostBaselineConfig | None = None,
    tuning_config: TuningConfig | None = None,
) -> tuple[ModelComparison, ...]:
    """Compare baseline and tuned models on the same outer test folds."""
    columns = list(feature_columns(asset_type))
    ordered = frame.reset_index(drop=True).copy()
    baseline_config = baseline_config or XGBoostBaselineConfig()
    folds: tuple[TimeSeriesFold, ...] = build_walk_forward_splits(
        len(ordered), n_splits=n_splits, test_size=test_size, gap=gap
    )
    results: list[ModelComparison] = []

    for index, fold in enumerate(folds, start=1):
        train = ordered.iloc[fold.train_start : fold.train_end]
        test = ordered.iloc[fold.test_start : fold.test_end]
        if train["target"].nunique() < 2:
            raise ValueError(f"fold {index} training target contains only one class")

        tuned = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
        )

        baseline_model = build_model(baseline_config)
        tuned_model = build_model(tuned.config)
        baseline_model.fit(train[columns], train["target"].astype(int))
        tuned_model.fit(train[columns], train["target"].astype(int))

        y_test = test["target"].astype(int)
        baseline_probability = baseline_model.predict_proba(test[columns])[:, 1]
        tuned_probability = tuned_model.predict_proba(test[columns])[:, 1]
        baseline_predicted = (baseline_probability >= 0.5).astype(int)
        tuned_predicted = (tuned_probability >= 0.5).astype(int)

        baseline_roc = _safe_roc_auc(y_test, baseline_probability)
        baseline_pr = _safe_pr_auc(y_test, baseline_probability)
        baseline_metrics = FoldMetrics(
            fold=index,
            train_end=fold.train_end,
            test_start=fold.test_start,
            test_end=fold.test_end,
            train_negative_count=int((train["target"] == 0).sum()),
            train_positive_count=int((train["target"] == 1).sum()),
            test_negative_count=int((y_test == 0).sum()),
            test_positive_count=int((y_test == 1).sum()),
            roc_auc=baseline_roc,
            pr_auc=baseline_pr,
            accuracy=float(accuracy_score(y_test, baseline_predicted)),
            precision=float(precision_score(y_test, baseline_predicted, zero_division=0)),
            recall=float(recall_score(y_test, baseline_predicted, zero_division=0)),
            positive_rate=float(y_test.mean()),
        )

        results.append(
            ModelComparison(
                fold=index,
                train_end=fold.train_end,
                test_start=fold.test_start,
                test_end=fold.test_end,
                baseline=baseline_metrics,
                tuned_config=tuned.config,
                tuned_roc_auc=_safe_roc_auc(y_test, tuned_probability),
                tuned_pr_auc=_safe_pr_auc(y_test, tuned_probability),
                tuned_accuracy=float(accuracy_score(y_test, tuned_predicted)),
                tuned_precision=float(precision_score(y_test, tuned_predicted, zero_division=0)),
                tuned_recall=float(recall_score(y_test, tuned_predicted, zero_division=0)),
            )
        )

    return tuple(results)
