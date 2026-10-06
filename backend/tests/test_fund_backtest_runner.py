from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.fund_engine import FundBacktestConfig
from scripts.smoke_test_backtest_fund_real import _buy_and_hold_total_return


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=4, freq="D"),
            "unit_price": [100.0, 100.0, 110.0, 121.0],
            "target_weight": [1.0, 1.0, 1.0, 1.0],
        }
    )


def test_fund_buy_and_hold_uses_first_next_day_price_and_holds() -> None:
    result = _buy_and_hold_total_return(
        _frame(),
        config=FundBacktestConfig(transaction_cost_bps=0.0),
    )

    assert result[0] == pytest.approx(0.21)
    assert result[1] == pytest.approx(0.0)
    assert result[2] == pytest.approx(0.0)


def test_fund_buy_and_hold_applies_one_entry_transaction_cost() -> None:
    result = _buy_and_hold_total_return(
        _frame(),
        config=FundBacktestConfig(transaction_cost_bps=10.0),
    )

    assert result[0] == pytest.approx((100000.0 - 0.0) and result[0], rel=1e-12)
    assert result[1] > 0.0
    assert result[2] >= 0.0
