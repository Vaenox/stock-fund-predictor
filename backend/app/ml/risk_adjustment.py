from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class RiskAdjustmentConfig:
    """Deterministic, explainable risk-penalty configuration."""

    low_volatility: float = 0.20
    high_volatility: float = 0.50
    low_volume_ratio: float = 0.50
    healthy_volume_ratio: float = 1.00
    stale_warning_days: int = 1
    stale_max_days: int = 3
    max_penalty: float = 20.0
    volatility_weight: float = 0.35
    trend_weakness_weight: float = 0.30
    liquidity_weight: float = 0.15
    data_quality_weight: float = 0.20

    def __post_init__(self) -> None:
        if self.low_volatility < 0 or self.high_volatility <= self.low_volatility:
            raise ValueError("volatility thresholds must be ordered and positive")
        if not 0 < self.low_volume_ratio < self.healthy_volume_ratio:
            raise ValueError("volume ratio thresholds must be ordered and positive")
        if self.stale_warning_days < 0 or self.stale_max_days <= self.stale_warning_days:
            raise ValueError("stale thresholds must be ordered and non-negative")
        if self.max_penalty < 0:
            raise ValueError("max_penalty cannot be negative")
        weights = (
            self.volatility_weight,
            self.trend_weakness_weight,
            self.liquidity_weight,
            self.data_quality_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("risk weights cannot be negative")
        if not np.isclose(sum(weights), 1.0):
            raise ValueError("risk weights must sum to 1.0")


@dataclass(frozen=True, slots=True)
class RiskAdjustmentResult:
    """Risk explanation plus the negative adjustment applied later to signals."""

    risk_score: float
    adjustment: float
    volatility_risk: float
    trend_weakness_risk: float
    liquidity_risk: float
    data_quality_risk: float
    reasons: tuple[str, ...]


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return float(np.clip(value, lower, upper))


def _value(row: pd.Series, column: str) -> float | None:
    value = row.get(column)
    if value is None or pd.isna(value):
        return None
    return float(value)


def _linear_risk(
    value: float | None,
    *,
    safe_value: float,
    danger_value: float,
) -> float:
    if value is None:
        return 50.0
    if danger_value <= safe_value:
        raise ValueError("danger_value must be greater than safe_value")
    return _clip((value - safe_value) / (danger_value - safe_value) * 100.0)


def _inverse_linear_risk(
    value: float | None,
    *,
    danger_value: float,
    safe_value: float,
) -> float:
    if value is None:
        return 50.0
    if safe_value <= danger_value:
        raise ValueError("safe_value must be greater than danger_value")
    return _clip((safe_value - value) / (safe_value - danger_value) * 100.0)


def _trend_weakness_risk(row: pd.Series) -> float:
    close = _value(row, "close")
    if close is None:
        close = _value(row, "unit_price")
    ema_20 = _value(row, "ema_20")
    ema_50 = _value(row, "ema_50")
    ema_200 = _value(row, "ema_200")

    checks: list[float] = []
    if close is not None and ema_20 is not None:
        checks.append(float(close < ema_20))
    if ema_20 is not None and ema_50 is not None:
        checks.append(float(ema_20 < ema_50))
    if ema_50 is not None and ema_200 is not None:
        checks.append(float(ema_50 < ema_200))

    if not checks:
        return 50.0
    return float(np.mean(checks) * 100.0)


def _stale_risk(stale_days: int, config: RiskAdjustmentConfig) -> float:
    if stale_days < 0:
        raise ValueError("stale_days cannot be negative")
    if stale_days <= config.stale_warning_days:
        return 0.0
    if stale_days >= config.stale_max_days:
        return 100.0
    span = config.stale_max_days - config.stale_warning_days
    return _clip((stale_days - config.stale_warning_days) / span * 100.0)


def _liquidity_risk(row: pd.Series, config: RiskAdjustmentConfig) -> float:
    return _inverse_linear_risk(
        _value(row, "volume_ratio_20"),
        danger_value=config.low_volume_ratio,
        safe_value=config.healthy_volume_ratio,
    )


def _weighted_score(parts: list[tuple[float, float]]) -> float:
    available = [(score, weight) for score, weight in parts if weight > 0]
    denominator = sum(weight for _, weight in available)
    if denominator <= 0:
        return 50.0
    return _clip(sum(score * weight for score, weight in available) / denominator)


def _result(
    *,
    volatility_risk: float,
    trend_weakness_risk: float,
    liquidity_risk: float,
    data_quality_risk: float,
    weights: RiskAdjustmentConfig,
) -> RiskAdjustmentResult:
    risk_score = _weighted_score(
        [
            (volatility_risk, weights.volatility_weight),
            (trend_weakness_risk, weights.trend_weakness_weight),
            (liquidity_risk, weights.liquidity_weight),
            (data_quality_risk, weights.data_quality_weight),
        ]
    )
    adjustment = -weights.max_penalty * (risk_score / 100.0)

    reasons: list[str] = []
    for name, value in (
        ("Volatilite riski", volatility_risk),
        ("Trend zayıflığı", trend_weakness_risk),
        ("Likidite riski", liquidity_risk),
        ("Veri kalitesi/stale", data_quality_risk),
    ):
        if value >= 70:
            reasons.append(f"{name}: yüksek ({value:.1f})")
        elif value <= 30:
            reasons.append(f"{name}: düşük ({value:.1f})")
        else:
            reasons.append(f"{name}: orta ({value:.1f})")

    return RiskAdjustmentResult(
        risk_score=_clip(risk_score),
        adjustment=float(adjustment),
        volatility_risk=_clip(volatility_risk),
        trend_weakness_risk=_clip(trend_weakness_risk),
        liquidity_risk=_clip(liquidity_risk),
        data_quality_risk=_clip(data_quality_risk),
        reasons=tuple(reasons),
    )


def calculate_stock_risk_adjustment(
    row: pd.Series,
    *,
    quality_ok: bool = True,
    stale_days: int = 0,
    config: RiskAdjustmentConfig | None = None,
) -> RiskAdjustmentResult:
    """Calculate a stock-only deterministic risk score and negative adjustment."""
    config = config or RiskAdjustmentConfig()
    volatility_risk = _linear_risk(
        _value(row, "volatility_20"),
        safe_value=config.low_volatility,
        danger_value=config.high_volatility,
    )
    trend_weakness_risk = _trend_weakness_risk(row)
    liquidity_risk = _liquidity_risk(row, config)
    data_quality_risk = max(
        100.0 if not quality_ok else 0.0,
        _stale_risk(stale_days, config),
    )
    return _result(
        volatility_risk=volatility_risk,
        trend_weakness_risk=trend_weakness_risk,
        liquidity_risk=liquidity_risk,
        data_quality_risk=data_quality_risk,
        weights=config,
    )


def calculate_fund_risk_adjustment(
    row: pd.Series,
    *,
    quality_ok: bool = True,
    stale_days: int = 0,
    config: RiskAdjustmentConfig | None = None,
) -> RiskAdjustmentResult:
    """Calculate a fund deterministic risk score without stock volume inputs."""
    if config is None:
        config = RiskAdjustmentConfig(
            volatility_weight=0.40,
            trend_weakness_weight=0.35,
            liquidity_weight=0.0,
            data_quality_weight=0.25,
        )
    elif config.liquidity_weight != 0:
        raise ValueError("fund risk config must set liquidity_weight to 0")

    volatility_risk = _linear_risk(
        _value(row, "volatility_20"),
        safe_value=config.low_volatility,
        danger_value=config.high_volatility,
    )
    trend_weakness_risk = _trend_weakness_risk(row)
    data_quality_risk = max(
        100.0 if not quality_ok else 0.0,
        _stale_risk(stale_days, config),
    )
    return _result(
        volatility_risk=volatility_risk,
        trend_weakness_risk=trend_weakness_risk,
        liquidity_risk=0.0,
        data_quality_risk=data_quality_risk,
        weights=config,
    )
