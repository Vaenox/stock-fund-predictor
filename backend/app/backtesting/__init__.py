"""Backtesting primitives for historical signal evaluation."""

from .engine import (
    BacktestConfig,
    BacktestResult,
    ExecutionCostConfig,
    run_long_only_backtest,
)
from .fund_engine import FundBacktestConfig, run_long_only_fund_backtest
from .metrics import BacktestMetrics, calculate_backtest_metrics
from .strategy import (
    SignalScoreBacktestResult,
    SignalScoreWeightConfig,
    map_signal_scores_to_target_weights,
    prepare_signal_score_backtest_frame,
    run_signal_score_backtest,
)

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "ExecutionCostConfig",
    "run_long_only_backtest",
    "FundBacktestConfig",
    "run_long_only_fund_backtest",
    "BacktestMetrics",
    "calculate_backtest_metrics",
    "SignalScoreBacktestResult",
    "SignalScoreWeightConfig",
    "map_signal_scores_to_target_weights",
    "prepare_signal_score_backtest_frame",
    "run_signal_score_backtest",
]
