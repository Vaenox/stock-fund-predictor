from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


META_FEATURE_COLUMNS = (
    "ml_probability",
    "technical_score",
    "risk_adjustment",
)


@dataclass(frozen=True, slots=True)
class SignalMetaConfig:
    """Configuration for deterministic, leakage-safe signal meta-aggregation."""

    C: float = 0.50
    max_iter: int = 1000
    random_state: int = 42

    def __post_init__(self) -> None:
        if self.C <= 0:
            raise ValueError("C must be positive")
        if self.max_iter <= 0:
            raise ValueError("max_iter must be positive")


def _validate_frame(frame: pd.DataFrame) -> None:
    required = [*META_FEATURE_COLUMNS, "target"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("missing required meta-signal columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("meta-signal frame cannot be empty")
    if frame[list(META_FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("meta-signal features contain missing values")
    if frame["target"].isna().any():
        raise ValueError("meta-signal target contains missing values")
    if frame["target"].nunique() < 2:
        raise ValueError("meta-signal target must contain both classes")


def build_signal_meta_model(
    frame: pd.DataFrame,
    *,
    config: SignalMetaConfig | None = None,
) -> Pipeline:
    """Fit a regularized logistic meta-model on leakage-safe OOF components."""
    _validate_frame(frame)
    config = config or SignalMetaConfig()

    model = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=config.C,
                    max_iter=config.max_iter,
                    random_state=config.random_state,
                ),
            ),
        ]
    )
    model.fit(
        frame[list(META_FEATURE_COLUMNS)],
        frame["target"].astype(int),
    )
    return model


def predict_signal_meta_probability(
    model: Pipeline,
    frame: pd.DataFrame,
) -> np.ndarray:
    """Predict positive-class probability from meta-signal components."""
    missing = [
        column for column in META_FEATURE_COLUMNS if column not in frame.columns
    ]
    if missing:
        raise ValueError("missing required meta-signal features: " + ", ".join(missing))
    if frame[list(META_FEATURE_COLUMNS)].isna().any().any():
        raise ValueError("meta-signal features contain missing values")

    probability = model.predict_proba(frame[list(META_FEATURE_COLUMNS)])[:, 1]
    return np.clip(np.asarray(probability, dtype=float), 0.0, 1.0)
