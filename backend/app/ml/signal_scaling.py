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



def derive_signal_scale_config(
    ml_probabilities: np.ndarray,
    technical_scores: np.ndarray,
    *,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
    ml_weight: float = 0.50,
    technical_weight: float = 0.30,
) -> SignalScaleConfig:
    """Derive normalization bounds from validation-period signal components.

    The supplied arrays must come from data that is chronologically prior to the
    data on which the returned configuration will be applied. This function only
    derives descriptive quantile bounds; it does not optimize thresholds against
    the target.
    """
    if not 0.0 <= lower_quantile < upper_quantile <= 1.0:
        raise ValueError("quantile bounds must satisfy 0 <= lower < upper <= 1")

    ml_values = np.asarray(ml_probabilities, dtype=float)
    technical_values = np.asarray(technical_scores, dtype=float)
    if ml_values.ndim != 1 or technical_values.ndim != 1:
        raise ValueError("signal component arrays must be one-dimensional")
    if ml_values.size == 0 or technical_values.size == 0:
        raise ValueError("signal component arrays cannot be empty")
    if ml_values.size != technical_values.size:
        raise ValueError("signal component arrays must have equal length")
    if not np.isfinite(ml_values).all():
        raise ValueError("ml probabilities must be finite")
    if not np.isfinite(technical_values).all():
        raise ValueError("technical scores must be finite")
    if ((ml_values < 0.0) | (ml_values > 1.0)).any():
        raise ValueError("ml probabilities must be between 0 and 1")
    if ((technical_values < 0.0) | (technical_values > 100.0)).any():
        raise ValueError("technical scores must be between 0 and 100")

    ml_floor, ml_ceiling = np.quantile(
        ml_values, [lower_quantile, upper_quantile]
    )
    technical_floor, technical_ceiling = np.quantile(
        technical_values, [lower_quantile, upper_quantile]
    )

    if ml_floor >= ml_ceiling:
        raise ValueError("derived ml probability bounds are not distinct")
    if technical_floor >= technical_ceiling:
        raise ValueError("derived technical bounds are not distinct")

    return SignalScaleConfig(
        ml_floor=float(ml_floor),
        ml_ceiling=float(ml_ceiling),
        technical_floor=float(technical_floor),
        technical_ceiling=float(technical_ceiling),
        ml_weight=ml_weight,
        technical_weight=technical_weight,
    )



def _empirical_percentile(value: float, reference: np.ndarray) -> float:
    """Map a value to its empirical percentile in a historical reference sample."""
    ordered = np.sort(reference)
    n = ordered.size
    if n < 2:
        raise ValueError("reference sample must contain at least two observations")
    if value <= ordered[0]:
        return 0.0
    if value >= ordered[-1]:
        return 100.0

    left = np.searchsorted(ordered, value, side="left")
    right = np.searchsorted(ordered, value, side="right")
    average_rank = ((left + right) / 2.0) - 0.5
    return float(np.clip(average_rank / n * 100.0, 0.0, 100.0))


def calculate_percentile_scaled_signal_base(
    ml_probability: float,
    technical_score: float,
    reference_ml_probabilities: np.ndarray,
    reference_technical_scores: np.ndarray,
    *,
    ml_weight: float = 0.50,
    technical_weight: float = 0.30,
) -> tuple[float, float, float]:
    """Scale signal components by their empirical percentile in prior OOF data.

    Reference samples must be chronologically prior to the observation being
    scored. No target or forward-return information is used.
    """
    if not 0.0 <= ml_probability <= 1.0:
        raise ValueError("ml_probability must be between 0 and 1")
    if not np.isfinite(technical_score):
        raise ValueError("technical_score must be finite")
    if ml_weight < 0 or technical_weight < 0:
        raise ValueError("score weights cannot be negative")
    denominator = ml_weight + technical_weight
    if denominator <= 0:
        raise ValueError("at least one score weight must be positive")

    ml_reference = np.asarray(reference_ml_probabilities, dtype=float)
    technical_reference = np.asarray(reference_technical_scores, dtype=float)
    if ml_reference.ndim != 1 or technical_reference.ndim != 1:
        raise ValueError("reference arrays must be one-dimensional")
    if ml_reference.size < 2 or technical_reference.size < 2:
        raise ValueError("reference samples must contain at least two observations")
    if not np.isfinite(ml_reference).all():
        raise ValueError("ml reference probabilities must be finite")
    if not np.isfinite(technical_reference).all():
        raise ValueError("technical reference scores must be finite")
    if ((ml_reference < 0.0) | (ml_reference > 1.0)).any():
        raise ValueError("ml reference probabilities must be between 0 and 1")
    if ((technical_reference < 0.0) | (technical_reference > 100.0)).any():
        raise ValueError("technical reference scores must be between 0 and 100")

    ml_scaled = _empirical_percentile(float(ml_probability), ml_reference)
    technical_scaled = _empirical_percentile(
        float(technical_score),
        technical_reference,
    )
    base = (
        ml_scaled * ml_weight
        + technical_scaled * technical_weight
    ) / denominator
    return ml_scaled, technical_scaled, float(np.clip(base, 0.0, 100.0))
