from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SignalScaleConfig:
    """Configuration for mapping heterogeneous model signals to a common score."""

    ml_floor: float = 0.02
    ml_ceiling: float = 0.50
    technical_floor: float = 30.0
    technical_ceiling: float = 85.0
    ml_weight: float = 0.50
    technical_weight: float = 0.30

    def __post_init__(self) -> None:
        if not 0.0 <= self.ml_floor < self.ml_ceiling <= 1.0:
            raise ValueError("ml probability bounds must satisfy 0 <= floor < ceiling <= 1")
        if not 0.0 <= self.technical_floor < self.technical_ceiling <= 100.0:
            raise ValueError("technical bounds must satisfy 0 <= floor < ceiling <= 100")
        if self.ml_weight < 0 or self.technical_weight < 0:
            raise ValueError("score weights cannot be negative")
        if self.ml_weight + self.technical_weight <= 0:
            raise ValueError("at least one score weight must be positive")


def _normalize(value: float, lower: float, upper: float) -> float:
    if upper <= lower:
        raise ValueError("upper bound must be greater than lower bound")
    return float(np.clip((value - lower) / (upper - lower) * 100.0, 0.0, 100.0))


def calculate_scaled_signal_base(
    ml_probability: float,
    technical_score: float,
    *,
    config: SignalScaleConfig | None = None,
) -> tuple[float, float, float]:
    """Return normalized ML, normalized technical, and weighted base score.

    Bounds are explicit configuration and must be validated on chronological
    validation data before production use. This function does not select bounds.
    """
    config = config or SignalScaleConfig()
    if not 0.0 <= ml_probability <= 1.0:
        raise ValueError("ml_probability must be between 0 and 1")
    if not np.isfinite(technical_score):
        raise ValueError("technical_score must be finite")

    ml_scaled = _normalize(
        float(ml_probability),
        config.ml_floor,
        config.ml_ceiling,
    )
    technical_scaled = _normalize(
        float(technical_score),
        config.technical_floor,
        config.technical_ceiling,
    )
    denominator = config.ml_weight + config.technical_weight
    base = (
        ml_scaled * config.ml_weight
        + technical_scaled * config.technical_weight
    ) / denominator
    return ml_scaled, technical_scaled, float(np.clip(base, 0.0, 100.0))
