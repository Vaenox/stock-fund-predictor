from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

CalibrationMethod = Literal["raw", "sigmoid", "isotonic"]


@dataclass(frozen=True, slots=True)
class CalibrationMetrics:
    method: CalibrationMethod
    brier: float
    log_loss: float
    pr_auc: float | None
    ece: float


@dataclass(frozen=True, slots=True)
class ProbabilityCalibrator:
    method: CalibrationMethod
    sigmoid_model: LogisticRegression | None = None
    isotonic_model: IsotonicRegression | None = None


def _clip_probability(values: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), 1e-6, 1.0 - 1e-6)


def _probability_for_ece(values: np.ndarray) -> np.ndarray:
    """Preserve exact 0/1 values for ECE while retaining finite inputs."""
    probability = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(probability)):
        raise ValueError("probability must contain only finite values")
    return np.clip(probability, 0.0, 1.0)


def _logit(values: np.ndarray) -> np.ndarray:
    probability = _clip_probability(values)
    return np.log(probability / (1.0 - probability))


def expected_calibration_error(
    y_true: np.ndarray,
    probability: np.ndarray,
    *,
    n_bins: int = 10,
) -> float:
    y = np.asarray(y_true, dtype=int)
    p = _probability_for_ece(probability)
    if y.shape != p.shape:
        raise ValueError("y_true and probability must have the same shape")
    if y.size == 0:
        raise ValueError("calibration input cannot be empty")
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    error = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (p >= left) & (
            p < right if right < 1.0 else p <= right
        )
        if not mask.any():
            continue
        error += (mask.sum() / y.size) * abs(
            y[mask].mean() - p[mask].mean()
        )
    return float(error)


def fit_probability_calibrator(
    method: CalibrationMethod,
    probability: np.ndarray,
    y_true: np.ndarray,
) -> ProbabilityCalibrator:
    y = np.asarray(y_true, dtype=int)
    p = _clip_probability(probability)
    if y.shape != p.shape:
        raise ValueError("probability and y_true must have the same shape")
    if y.size == 0:
        raise ValueError("calibration input cannot be empty")
    if np.unique(y).size < 2:
        raise ValueError("calibration target must contain both classes")

    if method == "raw":
        return ProbabilityCalibrator(method="raw")

    if method == "sigmoid":
        model = LogisticRegression(
            random_state=42,
            solver="lbfgs",
            max_iter=1000,
        )
        model.fit(_logit(p).reshape(-1, 1), y)
        return ProbabilityCalibrator(method="sigmoid", sigmoid_model=model)

    if method == "isotonic":
        model = IsotonicRegression(
            y_min=0.0,
            y_max=1.0,
            out_of_bounds="clip",
        )
        model.fit(p, y)
        return ProbabilityCalibrator(method="isotonic", isotonic_model=model)

    raise ValueError(f"unsupported calibration method: {method}")


def apply_probability_calibrator(
    calibrator: ProbabilityCalibrator,
    probability: np.ndarray,
) -> np.ndarray:
    p = _clip_probability(probability)
    if calibrator.method == "raw":
        return p
    if calibrator.method == "sigmoid":
        if calibrator.sigmoid_model is None:
            raise ValueError("sigmoid calibrator is not fitted")
        return _clip_probability(
            calibrator.sigmoid_model.predict_proba(_logit(p).reshape(-1, 1))[:, 1]
        )
    if calibrator.method == "isotonic":
        if calibrator.isotonic_model is None:
            raise ValueError("isotonic calibrator is not fitted")
        return _clip_probability(
            calibrator.isotonic_model.predict(p)
        )
    raise ValueError(f"unsupported calibration method: {calibrator.method}")


def evaluate_probability_calibration(
    method: CalibrationMethod,
    probability: np.ndarray,
    y_true: np.ndarray,
) -> CalibrationMetrics:
    y = np.asarray(y_true, dtype=int)
    p = _clip_probability(probability)
    if y.shape != p.shape:
        raise ValueError("probability and y_true must have the same shape")
    if y.size == 0:
        raise ValueError("calibration evaluation input cannot be empty")

    pr_auc = (
        float(average_precision_score(y, p))
        if np.unique(y).size >= 2
        else None
    )
    return CalibrationMetrics(
        method=method,
        brier=float(brier_score_loss(y, p)),
        log_loss=float(log_loss(y, p, labels=[0, 1])),
        pr_auc=pr_auc,
        ece=expected_calibration_error(y, p),
    )
