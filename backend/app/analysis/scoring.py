from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class TechnicalScoreConfig:
    """Deterministic heuristic weights for the pre-ML technical score.

    These are feature aggregation defaults, not backtested trading thresholds.
    They must be recalibrated only through out-of-sample evaluation before any
    production signal policy is defined.
    """

    trend_weight: float = 0.30
    momentum_weight: float = 0.30
    volatility_weight: float = 0.15
    volume_weight: float = 0.15
    breadth_weight: float = 0.10

    def __post_init__(self) -> None:
        weights = (
            self.trend_weight,
            self.momentum_weight,
            self.volatility_weight,
            self.volume_weight,
            self.breadth_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("technical score weights cannot be negative")
        if not np.isclose(sum(weights), 1.0):
            raise ValueError("technical score weights must sum to 1.0")


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return float(np.clip(value, lower, upper))


def _latest(row: pd.Series, *columns: str) -> dict[str, float | None]:
    return {column: (float(row[column]) if pd.notna(row[column]) else None) for column in columns}


def _signed_threshold_score(value: float | None, threshold: float) -> float:
    if value is None:
        return 50.0
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    return _clip(50.0 + 50.0 * (value / threshold))


def _rsi_score(value: float | None) -> float:
    if value is None:
        return 50.0
    if value <= 30.0:
        return _clip(35.0 + (value / 30.0) * 15.0)
    if value <= 50.0:
        return 50.0 + (value - 30.0)
    if value <= 70.0:
        return 70.0 + (value - 50.0)
    return _clip(90.0 - ((value - 70.0) * 2.0))


def _trend_score(row: pd.Series) -> tuple[float, dict[str, float | None]]:
    values = _latest(row, "close", "ema_20", "ema_50", "ema_200")
    close = values["close"]
    ema_20 = values["ema_20"]
    ema_50 = values["ema_50"]
    ema_200 = values["ema_200"]
    parts: list[float] = []

    if close is not None and ema_20 is not None:
        parts.append(_signed_threshold_score((close / ema_20) - 1.0, 0.05))
    if ema_20 is not None and ema_50 is not None:
        parts.append(_signed_threshold_score((ema_20 / ema_50) - 1.0, 0.05))
    if ema_50 is not None and ema_200 is not None:
        parts.append(_signed_threshold_score((ema_50 / ema_200) - 1.0, 0.10))
    if not parts:
        return 50.0, values
    return float(np.mean(parts)), values


def _momentum_score(row: pd.Series) -> tuple[float, dict[str, float | None]]:
    values = _latest(row, "rsi_14", "macd_hist", "momentum_5", "momentum_20")
    parts = [_rsi_score(values["rsi_14"])]
    parts.append(_signed_threshold_score(values["macd_hist"], 0.05))
    parts.append(_signed_threshold_score(values["momentum_5"], 0.05))
    parts.append(_signed_threshold_score(values["momentum_20"], 0.10))
    return float(np.mean(parts)), values


def _volatility_score(row: pd.Series) -> tuple[float, dict[str, float | None]]:
    values = _latest(row, "atr_pct_14", "volatility_20", "bb_position")
    parts: list[float] = []

    atr_pct = values["atr_pct_14"]
    if atr_pct is not None:
        parts.append(_clip(100.0 - (atr_pct / 0.10) * 100.0))

    volatility = values["volatility_20"]
    if volatility is not None:
        parts.append(_clip(100.0 - (volatility / 0.50) * 100.0))

    bb_position = values["bb_position"]
    if bb_position is not None:
        parts.append(_clip(50.0 + ((bb_position - 0.5) * 50.0)))

    if not parts:
        return 50.0, values
    return float(np.mean(parts)), values


def _volume_score(row: pd.Series) -> tuple[float, dict[str, float | None]]:
    values = _latest(row, "volume_ratio_20", "volume_change_1d")
    ratio = values["volume_ratio_20"]
    if ratio is None:
        return 50.0, values
    ratio_score = _clip((ratio / 2.0) * 100.0)
    change = values["volume_change_1d"]
    change_score = _signed_threshold_score(change, 0.50) if change is not None else 50.0
    return float((ratio_score * 0.75) + (change_score * 0.25)), values


def _breadth_score(row: pd.Series) -> tuple[float, dict[str, float | None]]:
    values = _latest(row, "adx_14", "bb_position")
    adx = values["adx_14"]
    bb_position = values["bb_position"]
    parts: list[float] = []
    if adx is not None:
        parts.append(_clip(adx / 50.0 * 100.0))
    if bb_position is not None:
        parts.append(_clip(50.0 + ((bb_position - 0.5) * 50.0)))
    if not parts:
        return 50.0, values
    return float(np.mean(parts)), values


def _component_reason(name: str, score: float, missing: bool = False) -> str:
    if missing:
        return f"{name}: veri yetersiz; nötr 50 puan kullanıldı"
    if score >= 70:
        return f"{name}: pozitif katkı ({score:.1f})"
    if score <= 30:
        return f"{name}: negatif katkı ({score:.1f})"
    return f"{name}: nötr/karışık görünüm ({score:.1f})"


def calculate_stock_technical_score(
    frame: pd.DataFrame,
    *,
    config: TechnicalScoreConfig | None = None,
) -> pd.DataFrame:
    """Add an explainable 0-100 stock technical score to an indicator frame."""
    config = config or TechnicalScoreConfig()
    if frame.empty:
        raise ValueError("technical score input cannot be empty")
    result = frame.sort_values("trading_date").reset_index(drop=True).copy()

    scores: list[float] = []
    trend_scores: list[float] = []
    momentum_scores: list[float] = []
    volatility_scores: list[float] = []
    volume_scores: list[float] = []
    breadth_scores: list[float] = []
    reasons: list[str] = []

    for _, row in result.iterrows():
        trend, trend_values = _trend_score(row)
        momentum, momentum_values = _momentum_score(row)
        volatility, volatility_values = _volatility_score(row)
        volume, volume_values = _volume_score(row)
        breadth, breadth_values = _breadth_score(row)

        final = (
            trend * config.trend_weight
            + momentum * config.momentum_weight
            + volatility * config.volatility_weight
            + volume * config.volume_weight
            + breadth * config.breadth_weight
        )
        scores.append(_clip(final))
        trend_scores.append(trend)
        momentum_scores.append(momentum)
        volatility_scores.append(volatility)
        volume_scores.append(volume)
        breadth_scores.append(breadth)

        reason_parts = [
            _component_reason("Trend", trend, all(value is None for value in trend_values.values())),
            _component_reason("Momentum", momentum, all(value is None for value in momentum_values.values())),
            _component_reason("Volatilite", volatility, all(value is None for value in volatility_values.values())),
            _component_reason("Hacim", volume, all(value is None for value in volume_values.values())),
            _component_reason("Trend gücü", breadth, all(value is None for value in breadth_values.values())),
        ]
        reasons.append(" | ".join(reason_parts))

    result["technical_score_trend"] = trend_scores
    result["technical_score_momentum"] = momentum_scores
    result["technical_score_volatility"] = volatility_scores
    result["technical_score_volume"] = volume_scores
    result["technical_score_breadth"] = breadth_scores
    result["technical_score"] = scores
    result["technical_score_reason"] = reasons
    return result


def calculate_fund_technical_score(
    frame: pd.DataFrame,
    *,
    config: TechnicalScoreConfig | None = None,
) -> pd.DataFrame:
    """Add an explainable 0-100 fund technical score.

    Fund inputs do not contain OHLCV, so unavailable stock-only components are
    neutralized and the available trend/momentum/volatility signals are
    reweighted deterministically.
    """
    config = config or TechnicalScoreConfig()
    if frame.empty:
        raise ValueError("technical score input cannot be empty")
    result = frame.sort_values("pricing_date").reset_index(drop=True).copy()
    scores: list[float] = []
    trend_scores: list[float] = []
    momentum_scores: list[float] = []
    volatility_scores: list[float] = []
    reasons: list[str] = []

    for _, row in result.iterrows():
        trend, trend_values = _trend_score(row)
        momentum, momentum_values = _momentum_score(row)
        volatility, volatility_values = _volatility_score(row)
        available = [(trend, config.trend_weight), (momentum, config.momentum_weight), (volatility, config.volatility_weight)]
        denominator = sum(weight for score, weight in available if any(value is not None for value in ({"trend": trend_values, "momentum": momentum_values, "volatility": volatility_values}["trend" if score == trend else "momentum" if score == momentum else "volatility"]).values()))
        if denominator == 0:
            final = 50.0
        else:
            final = sum(score * weight for score, weight in available) / denominator

        scores.append(_clip(final))
        trend_scores.append(trend)
        momentum_scores.append(momentum)
        volatility_scores.append(volatility)
        reasons.append(
            " | ".join(
                [
                    _component_reason("Trend", trend, all(value is None for value in trend_values.values())),
                    _component_reason("Momentum", momentum, all(value is None for value in momentum_values.values())),
                    _component_reason("Volatilite", volatility, all(value is None for value in volatility_values.values())),
                    "Hacim: fon verisinde desteklenmiyor",
                ]
            )
        )

    result["technical_score_trend"] = trend_scores
    result["technical_score_momentum"] = momentum_scores
    result["technical_score_volatility"] = volatility_scores
    result["technical_score_volume"] = np.nan
    result["technical_score_breadth"] = np.nan
    result["technical_score"] = scores
    result["technical_score_reason"] = reasons
    return result
