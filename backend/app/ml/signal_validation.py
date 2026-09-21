from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from app.ml.signal_rules import SignalRuleConfig, classify_signal


@dataclass(frozen=True, slots=True)
class SignalThresholdMetrics:
    sell_threshold: float
    buy_threshold: float
    total_count: int
    buy_count: int
    hold_count: int
    sell_count: int
    buy_coverage: float
    hold_coverage: float
    sell_coverage: float
    buy_target_rate: float | None
    hold_target_rate: float | None
    sell_target_rate: float | None
    buy_mean_forward_return: float | None
    hold_mean_forward_return: float | None
    sell_mean_forward_return: float | None


def _validate_frame(frame: pd.DataFrame) -> None:
    required = ("signal_score", "target", "forward_return_5d")
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("missing required validation columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("validation frame cannot be empty")
    if frame["signal_score"].isna().any():
        raise ValueError("signal_score contains missing values")
    if frame["target"].isna().any():
        raise ValueError("target contains missing values")
    if frame["forward_return_5d"].isna().any():
        raise ValueError("forward_return_5d contains missing values")


def _rate(values: pd.Series) -> float | None:
    if values.empty:
        return None
    return float(values.mean())


def _mean(values: pd.Series) -> float | None:
    if values.empty:
        return None
    return float(values.mean())


def evaluate_signal_thresholds(
    frame: pd.DataFrame,
    candidates: Iterable[SignalRuleConfig],
) -> tuple[SignalThresholdMetrics, ...]:
    """Evaluate threshold candidates without selecting a winning configuration.

    The function preserves candidate order and reports descriptive validation
    metrics so threshold decisions can be made separately from model training.
    """
    _validate_frame(frame)
    ordered = frame.reset_index(drop=True).copy()

    signal_scores = ordered["signal_score"].astype(float)
    targets = ordered["target"].astype(int)
    forward_returns = ordered["forward_return_5d"].astype(float)

    results: list[SignalThresholdMetrics] = []
    total = len(ordered)

    for config in candidates:
        labels = np.array(
            [
                classify_signal(score, config=config)
                for score in signal_scores.to_numpy()
            ],
            dtype=object,
        )
        masks = {
            "BUY": labels == "BUY",
            "HOLD": labels == "HOLD",
            "SELL": labels == "SELL",
        }

        counts = {label: int(mask.sum()) for label, mask in masks.items()}
        coverage = {label: counts[label] / total for label in masks}

        target_rates = {
            label: _rate(targets.loc[mask])
            for label, mask in masks.items()
        }
        mean_returns = {
            label: _mean(forward_returns.loc[mask])
            for label, mask in masks.items()
        }

        results.append(
            SignalThresholdMetrics(
                sell_threshold=config.sell_threshold,
                buy_threshold=config.buy_threshold,
                total_count=total,
                buy_count=counts["BUY"],
                hold_count=counts["HOLD"],
                sell_count=counts["SELL"],
                buy_coverage=coverage["BUY"],
                hold_coverage=coverage["HOLD"],
                sell_coverage=coverage["SELL"],
                buy_target_rate=target_rates["BUY"],
                hold_target_rate=target_rates["HOLD"],
                sell_target_rate=target_rates["SELL"],
                buy_mean_forward_return=mean_returns["BUY"],
                hold_mean_forward_return=mean_returns["HOLD"],
                sell_mean_forward_return=mean_returns["SELL"],
            )
        )

    return tuple(results)



@dataclass(frozen=True, slots=True)
class SignalScoreBinMetrics:
    bin_index: int
    lower_score: float
    upper_score: float
    count: int
    mean_score: float
    target_rate: float
    mean_forward_return: float


def evaluate_signal_score_bins(
    frame: pd.DataFrame,
    *,
    n_bins: int = 5,
) -> tuple[SignalScoreBinMetrics, ...]:
    """Evaluate target/return behavior across ascending signal-score bins.

    Bins are formed from score ranks so equal-sized groups remain available even
    when many observations share identical scores. The function is descriptive
    and does not choose thresholds or a scaling method.
    """
    _validate_frame(frame)
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")

    ordered = frame.reset_index(drop=True).copy()
    if len(ordered) < n_bins:
        n_bins = len(ordered)

    scores = ordered["signal_score"].astype(float)
    targets = ordered["target"].astype(int)
    forward_returns = ordered["forward_return_5d"].astype(float)

    ranks = scores.rank(method="first")
    bin_ids = np.floor((ranks - 1.0) * n_bins / len(ordered)).astype(int)

    results: list[SignalScoreBinMetrics] = []
    for bin_index in range(n_bins):
        mask = bin_ids == bin_index
        values = scores.loc[mask]
        if values.empty:
            continue
        results.append(
            SignalScoreBinMetrics(
                bin_index=bin_index + 1,
                lower_score=float(values.min()),
                upper_score=float(values.max()),
                count=int(mask.sum()),
                mean_score=float(values.mean()),
                target_rate=float(targets.loc[mask].mean()),
                mean_forward_return=float(forward_returns.loc[mask].mean()),
            )
        )

    return tuple(results)


def evaluate_signal_score_association(
    frame: pd.DataFrame,
) -> tuple[float, float]:
    """Return descriptive Spearman correlations with target and forward return."""
    _validate_frame(frame)
    scores = frame["signal_score"].astype(float)
    target = frame["target"].astype(float)
    forward_returns = frame["forward_return_5d"].astype(float)
    return (
        float(scores.corr(target, method="spearman")),
        float(scores.corr(forward_returns, method="spearman")),
    )
