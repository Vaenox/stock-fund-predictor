"""Backtesting primitives for historical signal evaluation."""

from .fund_diagnostics import (
    summarize_exposure,
    summarize_exposure_bands,
    summarize_signal_relationships,
    summarize_score_quintiles,
)
from .engine import (
    BacktestConfig,
    BacktestResult,
    ExecutionCostConfig,
    run_long_only_backtest,
)
from .fund_engine import (
    FundBacktestConfig,
    calculate_fund_buy_and_hold_total_return,
    run_long_only_fund_backtest,
)
from .metrics import BacktestMetrics, calculate_backtest_metrics
from .strategy import (
    SignalScoreBacktestResult,
    SignalScoreWeightConfig,
    map_signal_scores_to_target_weights,
    prepare_signal_score_backtest_frame,
    run_signal_score_backtest,
)

__all__ = [
    "summarize_exposure",
    "summarize_exposure_bands",
    "summarize_signal_relationships",
    "summarize_score_quintiles",
    "BacktestConfig",
    "BacktestResult",
    "ExecutionCostConfig",
    "run_long_only_backtest",
    "FundBacktestConfig",
    "calculate_fund_buy_and_hold_total_return",
    "run_long_only_fund_backtest",
    "BacktestMetrics",
    "calculate_backtest_metrics",
    "SignalScoreBacktestResult",
    "SignalScoreWeightConfig",
    "map_signal_scores_to_target_weights",
    "prepare_signal_score_backtest_frame",
    "run_signal_score_backtest",
]
