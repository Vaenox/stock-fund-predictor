from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import BacktestConfig, BacktestResult, run_long_only_backtest


@dataclass(frozen=True, slots=True)
class SignalScoreWeightConfig:
    """Map a continuous Phase 5 signal score to a long-only target weight.

    This is a position-sizing policy, not a BUY/HOLD/SELL threshold rule. A
    score at or below ``score_floor`` maps to zero exposure and a score at or
    above ``score_ceiling`` maps to ``maximum_weight``. Scores in between are
    mapped linearly.
    """

    score_floor: float = 0.0
    score_ceiling: float = 100.0
    maximum_weight: float = 1.0

    def __post_init__(self) -> None:
        values = (self.score_floor, self.score_ceiling, self.maximum_weight)
        if not all(np.isfinite(value) for value in values):
            raise ValueError("score-weight configuration values must be finite")
        if self.score_ceiling <= self.score_floor:
            raise ValueError("score_ceiling must be greater than score_floor")
        if not 0.0 <= self.maximum_weight <= 1.0:
            raise ValueError("maximum_weight must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class SignalScoreBacktestResult:
    """Backtest output together with its explicit score-to-weight input."""

    input_frame: pd.DataFrame
    backtest: BacktestResult


def map_signal_scores_to_target_weights(
    signal_scores: pd.Series,
    *,
    config: SignalScoreWeightConfig | None = None,
) -> pd.Series:
    """Convert finite continuous signal scores into bounded target weights."""
    config = config or SignalScoreWeightConfig()
    scores = pd.to_numeric(signal_scores, errors="raise")
    values = scores.to_numpy(dtype=float, copy=False)
    if not np.isfinite(values).all():
        raise ValueError("signal scores must be finite")

    normalized = (scores - config.score_floor) / (
        config.score_ceiling - config.score_floor
    )
    weights = normalized.clip(lower=0.0, upper=1.0) * config.maximum_weight
    return weights.rename("target_weight").astype(float)


def prepare_signal_score_backtest_frame(
    frame: pd.DataFrame,
    *,
    score_weight_config: SignalScoreWeightConfig | None = None,
    date_column: str = "date",
    signal_column: str = "signal_score",
    open_column: str = "open",
    close_column: str = "close",
) -> pd.DataFrame:
    """Prepare dated OOS signals for the leakage-safe engine.

    Each row represents information available on ``date_column``. The returned
    ``target_weight`` is therefore consumed by :func:`run_long_only_backtest`
    at the next available open, never at the row's own close.
    """
    required = {date_column, signal_column, open_column, close_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("signal backtest frame is missing columns: " + ", ".join(missing))
    if len(frame) < 2:
        raise ValueError("signal backtest requires at least two observations")

    result = pd.DataFrame(
        {
            "date": pd.to_datetime(frame[date_column], errors="raise"),
            "open": pd.to_numeric(frame[open_column], errors="raise"),
            "close": pd.to_numeric(frame[close_column], errors="raise"),
        }
    )
    if result["date"].duplicated().any():
        raise ValueError("signal backtest dates must be unique")
    if not np.isfinite(result[["open", "close"]].to_numpy(dtype=float)).all():
        raise ValueError("open and close must be finite")
    if (result[["open", "close"]] <= 0.0).any().any():
        raise ValueError("open and close must be positive")

    result["target_weight"] = map_signal_scores_to_target_weights(
        frame[signal_column],
        config=score_weight_config,
    ).to_numpy()
    return result.sort_values("date").reset_index(drop=True)


def run_signal_score_backtest(
    frame: pd.DataFrame,
    *,
    backtest_config: BacktestConfig | None = None,
    score_weight_config: SignalScoreWeightConfig | None = None,
    market: str | None = None,
    date_column: str = "date",
    signal_column: str = "signal_score",
    open_column: str = "open",
    close_column: str = "close",
) -> SignalScoreBacktestResult:
    """Run a continuous-signal historical backtest without choosing thresholds."""
    input_frame = prepare_signal_score_backtest_frame(
        frame,
        score_weight_config=score_weight_config,
        date_column=date_column,
        signal_column=signal_column,
        open_column=open_column,
        close_column=close_column,
    )
    return SignalScoreBacktestResult(
        input_frame=input_frame,
        backtest=run_long_only_backtest(
            input_frame,
            config=backtest_config,
            market=market,
        ),
    )
