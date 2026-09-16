from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

from app.analysis.features import AssetType, feature_columns
from app.ml.splitting import TimeSeriesFold, build_walk_forward_splits

TARGET_COLUMNS = {"target", "forward_return_5d"}


@dataclass(frozen=True, slots=True)
class XGBoostBaselineConfig:
    n_estimators: int = 200
    max_depth: int = 4
    learning_rate: float = 0.05
    subsample: float = 0.9
    colsample_bytree: float = 0.9
    min_child_weight: float = 1.0
    reg_lambda: float = 1.0
    random_state: int = 42

    def __post_init__(self) -> None:
        if self.n_estimators <= 0:
            raise ValueError("n_estimators must be positive")
        if self.max_depth <= 0:
            raise ValueError("max_depth must be positive")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        for name in ("subsample", "colsample_bytree"):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class FoldMetrics:
    fold: int
    train_end: int
    test_start: int
    test_end: int
    train_negative_count: int
    train_positive_count: int
    test_negative_count: int
    test_positive_count: int
    roc_auc: float | None
    pr_auc: float | None
    accuracy: float
    precision: float
    recall: float
    positive_rate: float


def _validate_training_frame(frame: pd.DataFrame, asset_type: AssetType) -> None:
    required = [*feature_columns(asset_type), "target"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("missing required training columns: " + ", ".join(missing))
    forbidden = TARGET_COLUMNS.intersection(feature_columns(asset_type))
    if forbidden:
        raise ValueError("target columns cannot be model features: " + ", ".join(sorted(forbidden)))
    if frame.empty:
        raise ValueError("training frame cannot be empty")
    if frame[list(feature_columns(asset_type))].isna().any().any():
        raise ValueError("training feature matrix contains missing values")
    if frame["target"].isna().any():
        raise ValueError("training target contains missing values")


def build_model(config: XGBoostBaselineConfig | None = None) -> XGBClassifier:
    config = config or XGBoostBaselineConfig()
    return XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=config.n_estimators,
        max_depth=config.max_depth,
        learning_rate=config.learning_rate,
        subsample=config.subsample,
        colsample_bytree=config.colsample_bytree,
        min_child_weight=config.min_child_weight,
        reg_lambda=config.reg_lambda,
        random_state=config.random_state,
        n_jobs=1,
        tree_method="hist",
    )


def fit_baseline_model(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    config: XGBoostBaselineConfig | None = None,
) -> XGBClassifier:
    _validate_training_frame(frame, asset_type)
    columns = list(feature_columns(asset_type))
    model = build_model(config)
    model.fit(frame[columns], frame["target"].astype(int))
    return model


def _safe_roc_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(roc_auc_score(y_true, probability))


def _safe_pr_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(average_precision_score(y_true, probability))


def evaluate_walk_forward(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    n_splits: int = 3,
    test_size: int | None = None,
    gap: int = 5,
    config: XGBoostBaselineConfig | None = None,
) -> tuple[FoldMetrics, ...]:
    """Evaluate the baseline chronologically without crossing the target horizon gap."""
    _validate_training_frame(frame, asset_type)
    if gap < 5:
        raise ValueError("gap must be at least the 5-observation target horizon")

    ordered = frame.reset_index(drop=True).copy()
    folds: tuple[TimeSeriesFold, ...] = build_walk_forward_splits(
        len(ordered), n_splits=n_splits, test_size=test_size, gap=gap
    )
    columns = list(feature_columns(asset_type))
    metrics: list[FoldMetrics] = []

    for index, fold in enumerate(folds, start=1):
        train = ordered.iloc[fold.train_start : fold.train_end]
        test = ordered.iloc[fold.test_start : fold.test_end]
        if train["target"].nunique() < 2:
            raise ValueError(f"fold {index} training target contains only one class")

        model = build_model(config)
        model.fit(train[columns], train["target"].astype(int))
        probability = model.predict_proba(test[columns])[:, 1]
        predicted = (probability >= 0.5).astype(int)

        y_train = train["target"].astype(int)
        y_test = test["target"].astype(int)
        train_counts = y_train.value_counts().to_dict()
        test_counts = y_test.value_counts().to_dict()
        metrics.append(
            FoldMetrics(
                fold=index,
                train_end=fold.train_end,
                test_start=fold.test_start,
                test_end=fold.test_end,
                train_negative_count=int(train_counts.get(0, 0)),
                train_positive_count=int(train_counts.get(1, 0)),
                test_negative_count=int(test_counts.get(0, 0)),
                test_positive_count=int(test_counts.get(1, 0)),
                roc_auc=_safe_roc_auc(y_test, probability),
                pr_auc=_safe_pr_auc(y_test, probability),
                accuracy=float(accuracy_score(y_test, predicted)),
                precision=float(precision_score(y_test, predicted, zero_division=0)),
                recall=float(recall_score(y_test, predicted, zero_division=0)),
                positive_rate=float(y_test.mean()),
            )
        )

    return tuple(metrics)
