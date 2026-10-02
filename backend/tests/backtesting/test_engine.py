from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.engine import BacktestConfig, run_long_only_backtest


def _frame(targets: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(targets), freq="D"),
            "open": [100.0, 100.0, 110.0, 121.0][: len(targets)],
            "close": [100.0, 110.0, 121.0, 121.0][: len(targets)],
            "target_weight": targets,
        }
    )


def test_target_is_executed_at_next_open_not_same_day_close() -> None:
    result = run_long_only_backtest(
        _frame([1.0, 1.0, 1.0, 1.0]),
        config=BacktestConfig(transaction_cost_bps=0.0, slippage_bps=0.0),
    )

    first_trade = result.trade_log.iloc[0]

    assert first_trade["signal_date"] == pd.Timestamp("2026-01-01")
    assert first_trade["execution_date"] == pd.Timestamp("2026-01-02")
    assert first_trade["execution_price"] == pytest.approx(100.0)


def test_transaction_cost_reduces_equity() -> None:
    frame = _frame([1.0, 1.0, 1.0, 0.0])

    no_cost = run_long_only_backtest(
        frame,
        config=BacktestConfig(transaction_cost_bps=0.0, slippage_bps=0.0),
    )
    with_cost = run_long_only_backtest(
        frame,
        config=BacktestConfig(transaction_cost_bps=10.0, slippage_bps=0.0),
    )

    assert with_cost.metrics.total_transaction_cost == pytest.approx(200.0)
    assert with_cost.metrics.total_transaction_cost > no_cost.metrics.total_transaction_cost
    assert with_cost.metrics.total_return < no_cost.metrics.total_return


def test_slippage_cost_reduces_buy_execution_value() -> None:
    frame = _frame([1.0, 1.0, 1.0])

    no_slippage = run_long_only_backtest(
        frame,
        config=BacktestConfig(transaction_cost_bps=0.0, slippage_bps=0.0),
    )
    with_slippage = run_long_only_backtest(
        frame,
        config=BacktestConfig(transaction_cost_bps=0.0, slippage_bps=5.0),
    )

    first_trade = with_slippage.trade_log.iloc[0]

    assert first_trade["execution_price"] == pytest.approx(100.05)
    assert with_slippage.metrics.total_slippage_cost > 0.0
    assert with_slippage.metrics.total_return < no_slippage.metrics.total_return


def test_last_signal_is_not_executed_without_next_open() -> None:
    result = run_long_only_backtest(
        _frame([0.0, 0.0, 1.0]),
        config=BacktestConfig(transaction_cost_bps=0.0, slippage_bps=0.0),
    )

    assert result.trade_log.empty
    assert result.equity_curve.iloc[-1]["target_weight"] == pytest.approx(0.0)


def test_target_weight_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValueError, match="target_weight must be between 0 and 1"):
        run_long_only_backtest(_frame([0.0, 1.2, 0.0]))


def test_backtest_requires_unique_dates() -> None:
    frame = _frame([0.0, 1.0, 0.0])
    frame.loc[2, "date"] = frame.loc[1, "date"]

    with pytest.raises(ValueError, match="dates must be unique"):
        run_long_only_backtest(frame)


def test_backtest_requires_positive_prices() -> None:
    frame = _frame([0.0, 1.0, 0.0])
    frame.loc[1, "open"] = 0.0

    with pytest.raises(ValueError, match="open and close must be positive"):
        run_long_only_backtest(frame)
