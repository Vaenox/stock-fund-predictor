from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.metrics import calculate_backtest_metrics


def test_metrics_calculate_return_drawdown_and_win_rate() -> None:
    equity = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "equity": [100.0, 110.0, 99.0, 108.9, 130.68],
            "net_return": [0.0, 0.10, -0.10, 0.10, 0.20],
        }
    )

    metrics = calculate_backtest_metrics(
        equity,
        initial_capital=100.0,
        periods_per_year=252,
        total_transaction_cost=1.5,
        total_slippage_cost=0.5,
        total_turnover=1.75,
    )

    assert metrics.total_return == pytest.approx(0.3068)
    assert metrics.maximum_drawdown == pytest.approx(-0.10)
    assert metrics.win_rate == pytest.approx(0.75)
    assert metrics.total_transaction_cost == pytest.approx(1.5)
    assert metrics.total_slippage_cost == pytest.approx(0.5)
    assert metrics.total_turnover == pytest.approx(1.75)


def test_profit_factor_and_zero_loss_behavior() -> None:
    profitable = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "equity": [100.0, 110.0, 121.0],
            "net_return": [0.0, 0.10, 0.10],
        }
    )

    metrics = calculate_backtest_metrics(
        profitable,
        initial_capital=100.0,
        periods_per_year=252,
    )

    assert metrics.profit_factor == float("inf")


def test_empty_equity_curve_is_rejected() -> None:
    frame = pd.DataFrame(columns=["date", "equity", "net_return"])

    with pytest.raises(ValueError, match="equity curve cannot be empty"):
        calculate_backtest_metrics(frame, initial_capital=100.0)
