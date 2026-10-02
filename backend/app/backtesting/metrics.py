from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Mapping

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    maximum_drawdown: float
    win_rate: float
    profit_factor: float
    total_transaction_cost: float
    total_slippage_cost: float
    total_turnover: float


def _validate_equity_curve(equity_curve: pd.DataFrame) -> None:
    required = {"date", "equity", "net_return"}
    missing = sorted(required - set(equity_curve.columns))
    if missing:
        raise ValueError("equity curve is missing columns: " + ", ".join(missing))
    if equity_curve.empty:
        raise ValueError("equity curve cannot be empty")
    equity = equity_curve["equity"].astype(float)
    if not np.isfinite(equity).all() or (equity <= 0).any():
        raise ValueError("equity must contain finite positive values")


def calculate_backtest_metrics(
    equity_curve: pd.DataFrame,
    *,
    initial_capital: float,
    periods_per_year: int = 252,
    total_transaction_cost: float = 0.0,
    total_slippage_cost: float = 0.0,
    total_turnover: float = 0.0,
) -> BacktestMetrics:
    """Calculate descriptive portfolio metrics from a net equity curve."""
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

    _validate_equity_curve(equity_curve)

    equity = equity_curve["equity"].astype(float)
    returns = equity_curve["net_return"].astype(float)
    if not np.isfinite(returns).all():
        raise ValueError("net_return must contain finite values")

    total_return = float(equity.iloc[-1] / initial_capital - 1.0)

    n_periods = len(equity)
    annualized_return = float(
        (equity.iloc[-1] / initial_capital) ** (periods_per_year / n_periods) - 1.0
    )

    if len(returns) > 1:
        volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year))
    else:
        volatility = 0.0

    if volatility > 0:
        sharpe_ratio = float(
            returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year)
        )
    else:
        sharpe_ratio = 0.0

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    maximum_drawdown = float(drawdown.min())

    non_zero_returns = returns[returns != 0]
    win_rate = (
        float((non_zero_returns > 0).mean())
        if not non_zero_returns.empty
        else 0.0
    )

    gains = float(returns[returns > 0].sum())
    losses = float(-returns[returns < 0].sum())
    profit_factor = gains / losses if losses > 0 else inf

    return BacktestMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_volatility=volatility,
        sharpe_ratio=sharpe_ratio,
        maximum_drawdown=maximum_drawdown,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_transaction_cost=float(total_transaction_cost),
        total_slippage_cost=float(total_slippage_cost),
        total_turnover=float(total_turnover),
    )
