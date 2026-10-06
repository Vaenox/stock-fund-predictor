from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.fund_engine import (
    FundBacktestConfig,
    run_long_only_fund_backtest,
)


def _frame(targets: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(targets), freq="D"),
            "unit_price": [100.0, 100.0, 110.0, 121.0][: len(targets)],
            "target_weight": targets,
        }
    )


def test_fund_target_executes_at_next_day_unit_price() -> None:
    result = run_long_only_fund_backtest(
        _frame([1.0, 1.0, 1.0]),
        config=FundBacktestConfig(transaction_cost_bps=0.0),
    )

    first_trade = result.trade_log.iloc[0]

    assert first_trade["signal_date"] == pd.Timestamp("2026-01-01")
    assert first_trade["execution_date"] == pd.Timestamp("2026-01-02")
    assert first_trade["execution_unit_price"] == pytest.approx(100.0)


def test_fund_last_signal_is_not_executed_without_next_unit_price() -> None:
    result = run_long_only_fund_backtest(
        _frame([0.0, 0.0, 1.0]),
        config=FundBacktestConfig(transaction_cost_bps=0.0),
    )

    assert result.trade_log.empty
    assert result.equity_curve.iloc[-1]["target_weight"] == pytest.approx(0.0)


def test_fund_transaction_cost_reduces_equity() -> None:
    frame = _frame([1.0, 1.0, 0.0, 0.0])

    no_cost = run_long_only_fund_backtest(
        frame,
        config=FundBacktestConfig(transaction_cost_bps=0.0),
    )
    with_cost = run_long_only_fund_backtest(
        frame,
        config=FundBacktestConfig(transaction_cost_bps=10.0),
    )

    assert with_cost.metrics.total_transaction_cost > 0.0
    assert with_cost.metrics.total_return < no_cost.metrics.total_return
    assert with_cost.metrics.total_slippage_cost == pytest.approx(0.0)
    assert (with_cost.equity_curve["cash"] >= 0.0).all()


def test_fund_engine_never_reports_slippage_execution() -> None:
    result = run_long_only_fund_backtest(
        _frame([1.0, 1.0, 1.0]),
        config=FundBacktestConfig(transaction_cost_bps=10.0),
    )

    assert result.execution_costs.slippage_bps == pytest.approx(0.0)
    assert result.metrics.total_slippage_cost == pytest.approx(0.0)
    assert (result.trade_log["slippage_cost"] == 0.0).all()


def test_fund_buy_sizing_includes_transaction_cost_without_negative_cash() -> None:
    result = run_long_only_fund_backtest(
        _frame([1.0, 1.0, 1.0]),
        config=FundBacktestConfig(transaction_cost_bps=10.0),
    )

    assert (result.equity_curve["cash"] >= 0.0).all()


def test_fund_target_weight_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValueError, match="target_weight must be between 0 and 1"):
        run_long_only_fund_backtest(_frame([0.0, 1.2, 0.0]))


def test_fund_requires_unique_dates() -> None:
    frame = _frame([0.0, 1.0, 0.0])
    frame.loc[2, "date"] = frame.loc[1, "date"]

    with pytest.raises(ValueError, match="dates must be unique"):
        run_long_only_fund_backtest(frame)


def test_fund_requires_positive_unit_price() -> None:
    frame = _frame([0.0, 1.0, 0.0])
    frame.loc[1, "unit_price"] = 0.0

    with pytest.raises(ValueError, match="unit_price must be positive"):
        run_long_only_fund_backtest(frame)


def test_fund_config_rejects_negative_cost() -> None:
    with pytest.raises(ValueError, match="transaction_cost_bps"):
        FundBacktestConfig(transaction_cost_bps=-1.0)
