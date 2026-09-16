from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import pandas as pd

from app.analysis.features import AssetType, feature_columns
from app.ml.splitting import TimeSeriesFold, build_walk_forward_splits
from app.ml.xgboost_baseline import XGBoostBaselineConfig, build_model


@dataclass(frozen=True, slots=True)
class TuningConfig:
    n_inner_splits: int = 2
    inner_test_size: int = 20
    gap: int = 5

    def __post_init__(self) -> None:
        if self.n_inner_splits <= 0:
            raise ValueError("n_inner_splits must be positive")
        if self.inner_test_size <= 0:
            raise ValueError("inner_test_size must be positive")
        if self.gap < 5:
            raise ValueError("gap must be at least the 5-observation target horizon")


@dataclass(frozen=True, slots=True)
class TuningCandidate:
    config: XGBoostBaselineConfig
    score: float


def build_inner_splits(
    n_training_samples: int,
    *,
    config: TuningConfig | None = None,
) -> tuple[TimeSeriesFold, ...]:
    config = config or TuningConfig()
    return build_walk_forward_splits(
        n_training_samples,
        n_splits=config.n_inner_splits,
        test_size=config.inner_test_size,
        gap=config.gap,
    )


def _validate_tuning_frame(frame: pd.DataFrame, asset_type: AssetType) -> None:
    columns = list(feature_columns(asset_type))
    required = [*columns, "target"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("missing required tuning columns: " + ", ".join(missing))
    if frame[columns].isna().any().any():
        raise ValueError("tuning feature matrix contains missing values")
    if frame["target"].isna().any():
        raise ValueError("tuning target contains missing values")
    if frame.empty:
        raise ValueError("tuning frame cannot be empty")


def _score_probability(y_true: pd.Series, probability: pd.Series) -> float:
    from sklearn.metrics import average_precision_score

    if y_true.nunique() < 2:
        return float("nan")
    return float(average_precision_score(y_true.astype(int), probability))


def evaluate_candidate_inner(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    candidate: XGBoostBaselineConfig,
    tuning_config: TuningConfig | None = None,
) -> float:
    """Score one candidate only inside the supplied outer-training period."""
    _validate_tuning_frame(frame, asset_type)
    columns = list(feature_columns(asset_type))
    folds = build_inner_splits(len(frame), config=tuning_config)
    fold_scores: list[float] = []

    for fold in folds:
        train = frame.iloc[fold.train_start : fold.train_end]
        validation = frame.iloc[fold.test_start : fold.test_end]
        if train["target"].nunique() < 2:
            raise ValueError("inner training target contains only one class")
        model = build_model(candidate)
        model.fit(train[columns], train["target"].astype(int))
        probability = model.predict_proba(validation[columns])[:, 1]
        score = _score_probability(validation["target"], pd.Series(probability, index=validation.index))
        if pd.notna(score):
            fold_scores.append(score)

    if not fold_scores:
        raise ValueError("inner validation has no two-class fold")
    return float(sum(fold_scores) / len(fold_scores))


def default_candidate_grid(*, random_state: int = 42) -> tuple[XGBoostBaselineConfig, ...]:
    """Small deterministic grid suitable for the first real-data tuning pass."""
    candidates = []
    for max_depth, learning_rate, min_child_weight in product((3, 4, 5), (0.03, 0.05), (1.0, 3.0)):
        candidates.append(
            XGBoostBaselineConfig(
                n_estimators=200,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.9,
                colsample_bytree=0.9,
                min_child_weight=min_child_weight,
                reg_lambda=1.0,
                random_state=random_state,
            )
        )
    return tuple(candidates)


def select_best_candidate(
    frame: pd.DataFrame,
    *,
    asset_type: AssetType,
    candidates: tuple[XGBoostBaselineConfig, ...] | None = None,
    tuning_config: TuningConfig | None = None,
) -> TuningCandidate:
    """Select a candidate using only inner chronological validation PR-AUC."""
    candidates = candidates or default_candidate_grid()
    if not candidates:
        raise ValueError("candidate grid cannot be empty")

    scored: list[TuningCandidate] = []
    for candidate in candidates:
        score = evaluate_candidate_inner(
            frame,
            asset_type=asset_type,
            candidate=candidate,
            tuning_config=tuning_config,
        )
        scored.append(TuningCandidate(config=candidate, score=score))

    return max(
        scored,
        key=lambda item: (
            item.score,
            -item.config.max_depth,
            -item.config.learning_rate,
            -item.config.min_child_weight,
        ),
    )
