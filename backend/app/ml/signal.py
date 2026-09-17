from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SignalScoreConfig:
    """Deterministic weights for combining ML, technical, and risk inputs."""

    ml_weight: float = 0.50
    technical_weight: float = 0.30
    risk_weight: float = 0.20

    def __post_init__(self) -> None:
        weights = (self.ml_weight, self.technical_weight, self.risk_weight)
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
    """Combine model probability, technical score and risk adjustment deterministically.

    ``ml_probability`` is converted to a 0-100 contribution. ``technical_score``
    is already 0-100. ``risk_adjustment`` is a negative penalty, so it is added
    after the weighted ML + technical + risk baseline score and then clipped.

    ``risk_weight`` is retained as the explicit maximum influence allocation of
    the risk component. Because the current risk adjustment is already expressed
    as a bounded negative score (0 .. -max_penalty), multiplying it by
    ``risk_weight`` would double-discount the configured risk penalty. Therefore
    the risk weight is validated as part of the configuration contract but the
    realized penalty is applied directly.
    """
    config = config or SignalScoreConfig()
    if not 0.0 <= ml_probability <= 1.0:
        raise ValueError("ml_probability must be between 0 and 1")
    technical_score = _clip(float(technical_score))
    if risk_adjustment > 0.0:
        raise ValueError("risk_adjustment must be non-positive")

    base_score = (
        (ml_probability * 100.0 * config.ml_weight)
        + (technical_score * config.technical_weight)
    )
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
