from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.fund_engine import (
    FundBacktestConfig,
    calculate_fund_buy_and_hold_total_return,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=4, freq="D"),
            "unit_price": [100.0, 100.0, 110.0, 121.0],
            "target_weight": [1.0, 1.0, 1.0, 1.0],
        }
    )


def test_fund_buy_and_hold_uses_first_next_day_price_and_holds() -> None:
    result = calculate_fund_buy_and_hold_total_return(
        _frame(),
        config=FundBacktestConfig(transaction_cost_bps=0.0),
    )

    assert result[0] == pytest.approx(0.21)
    assert result[1] == pytest.approx(0.0)
    assert result[2] == pytest.approx(0.0)


def test_fund_buy_and_hold_applies_one_entry_transaction_cost() -> None:
    result = calculate_fund_buy_and_hold_total_return(
        _frame(),
        config=FundBacktestConfig(transaction_cost_bps=10.0),
    )

    expected_return = (121.0 / 100.0) / 1.001 - 1.0
    expected_cost = 100_000.0 * 0.001 / 1.001

    assert result[0] == pytest.approx(expected_return)
    assert result[1] == pytest.approx(expected_cost)
    assert result[2] == pytest.approx(0.0, abs=1e-8)
