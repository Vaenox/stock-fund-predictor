from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SignalScoreConfig:
    """Deterministic relative weights for ML and technical signal inputs.

    Risk is intentionally kept as a separate bounded negative adjustment. The
    ML and technical weights are normalized to their own total so the
    pre-risk signal remains on the full 0-100 scale.
    """

    ml_weight: float = 0.50
    technical_weight: float = 0.30

    def __post_init__(self) -> None:
        weights = (self.ml_weight, self.technical_weight)
        if any(weight < 0 for weight in weights):
            raise ValueError("signal weights cannot be negative")
        if not np.isclose(sum(weights), 1.0):
            raise ValueError("signal weights must sum to 1.0")


@dataclass(frozen=True, slots=True)
class SignalScoreResult:
    ml_probability: float
    technical_score: float
    risk_adjustment: float
    signal_score: float
    reasons: tuple[str, ...]


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return float(np.clip(value, lower, upper))


def calculate_signal_score(
    ml_probability: float,
    technical_score: float,
    risk_adjustment: float,
    *,
    config: SignalScoreConfig | None = None,
) -> SignalScoreResult:
    """Combine model probability, technical score and risk adjustment.

    ML probability and technical score are weighted on a normalized 0-100
    scale. Risk adjustment is already a bounded negative penalty produced by
    the separate risk layer, so it is added directly once.
    """
    config = config or SignalScoreConfig()
    if not 0.0 <= ml_probability <= 1.0:
        raise ValueError("ml_probability must be between 0 and 1")
    technical_score = _clip(float(technical_score))
    if risk_adjustment > 0.0:
        raise ValueError("risk_adjustment must be non-positive")

    weight_total = config.ml_weight + config.technical_weight
    base_score = (
        (ml_probability * 100.0 * config.ml_weight)
        + (technical_score * config.technical_weight)
    ) / weight_total
    signal_score = _clip(base_score + risk_adjustment)

    reasons: list[str] = []
    reasons.append(f"ML olasılığı: {ml_probability * 100.0:.1f}")
    reasons.append(f"Teknik skor: {technical_score:.1f}")
    reasons.append(f"Risk adjustment: {risk_adjustment:.1f}")
    if risk_adjustment < 0:
        reasons.append("Risk cezası final skoru aşağı çekti")
    else:
        reasons.append("Risk cezası uygulanmadı")

    return SignalScoreResult(
        ml_probability=float(ml_probability),
        technical_score=technical_score,
        risk_adjustment=float(risk_adjustment),
        signal_score=signal_score,
        reasons=tuple(reasons),
    )
