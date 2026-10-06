from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import BacktestResult, ExecutionCostConfig
from .metrics import calculate_backtest_metrics


@dataclass(frozen=True, slots=True)
class FundBacktestConfig:
    """Execution assumptions for daily fund unit-price backtests."""

    initial_capital: float = 100_000.0
    transaction_cost_bps: float = 10.0
    periods_per_year: int = 252

    def __post_init__(self) -> None:
        if not np.isfinite(self.initial_capital) or self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive and finite")
        if not np.isfinite(self.transaction_cost_bps) or self.transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps must be finite and non-negative")
        if self.periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")


def calculate_fund_buy_and_hold_total_return(
    frame: pd.DataFrame,
    *,
    config: FundBacktestConfig,
) -> tuple[float, float, float]:
    """Calculate true first-next-day-price to final-price fund buy-and-hold."""
    if len(frame) < 2:
        raise ValueError("fund buy-and-hold requires at least two observations")

    opening = float(frame.iloc[1]["unit_price"])
    final_price = float(frame.iloc[-1]["unit_price"])
    capital = float(config.initial_capital)
    fee_rate = config.transaction_cost_bps / 10_000.0

    units = capital / (opening * (1.0 + fee_rate))
    trade_notional = units * opening
    transaction_cost = trade_notional * fee_rate
    cash = capital - trade_notional - transaction_cost

    if abs(cash) < 1e-8:
        cash = 0.0
    if cash < -1e-8:
        raise AssertionError("fund buy-and-hold produced negative cash")

    final_equity = cash + units * final_price
    return (
        final_equity / capital - 1.0,
        transaction_cost,
        cash,
    )


def _validate_fund_input(
    frame: pd.DataFrame,
    date_column: str,
    price_column: str,
    target_column: str,
) -> pd.DataFrame:
    required = {date_column, price_column, target_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("fund backtest frame is missing columns: " + ", ".join(missing))
    if len(frame) < 2:
        raise ValueError("fund backtest requires at least two observations")

    result = frame.copy()
    result[date_column] = pd.to_datetime(result[date_column], errors="raise")
    if result[date_column].duplicated().any():
        raise ValueError("fund backtest dates must be unique")
    result = result.sort_values(date_column).reset_index(drop=True)

    for column in (price_column, target_column):
        result[column] = pd.to_numeric(result[column], errors="raise")

    values = result[[price_column, target_column]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("unit_price and target_weight must be finite")
    if (result[price_column] <= 0.0).any():
        raise ValueError("unit_price must be positive")
    if not result[target_column].between(0.0, 1.0).all():
        raise ValueError("target_weight must be between 0 and 1")

    return result


def run_long_only_fund_backtest(
    frame: pd.DataFrame,
    *,
    config: FundBacktestConfig | None = None,
    date_column: str = "date",
    price_column: str = "unit_price",
    target_column: str = "target_weight",
) -> BacktestResult:
    """Run a long-only fund backtest using next-day unit-price execution.

    A target weight observed at date t is executed at date t+1's published
    unit price. Funds do not use stock-style open/slippage semantics here.
    Transaction costs are applied to traded notional; slippage cost is always
    zero because this contract does not model a bid/ask execution price.
    """
    config = config or FundBacktestConfig()
    data = _validate_fund_input(
        frame,
        date_column=date_column,
        price_column=price_column,
        target_column=target_column,
    )

    cash = config.initial_capital
    units = 0.0
    previous_equity = config.initial_capital
    fee_rate = config.transaction_cost_bps / 10_000.0

    equity_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []
    total_fee = 0.0
    total_turnover = 0.0

    for index in range(len(data) - 1):
        signal_row = data.iloc[index]
        execution_row = data.iloc[index + 1]

        signal_date = signal_row[date_column]
        execution_date = execution_row[date_column]
        target_weight = float(signal_row[target_column])

        signal_unit_price = float(signal_row[price_column])
        execution_unit_price = float(execution_row[price_column])

        equity_at_signal = cash + units * signal_unit_price
        desired_position_value = equity_at_signal * target_weight
        desired_units = desired_position_value / execution_unit_price

        if desired_units > units:
            max_affordable_units = max(cash, 0.0) / (
                execution_unit_price * (1.0 + fee_rate)
            )
            desired_units = min(desired_units, units + max_affordable_units)

        unit_delta = desired_units - units
        trade_notional = abs(unit_delta) * execution_unit_price
        transaction_cost = trade_notional * fee_rate

        if unit_delta > 0:
            cash -= unit_delta * execution_unit_price
        elif unit_delta < 0:
            cash += (-unit_delta) * execution_unit_price

        cash -= transaction_cost
        units = desired_units

        equity = cash + units * execution_unit_price
        net_return = equity / previous_equity - 1.0
        turnover = (
            trade_notional / equity_at_signal
            if equity_at_signal > 0.0
            else 0.0
        )

        if unit_delta != 0.0:
            trade_rows.append(
                {
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "target_weight": target_weight,
                    "unit_delta": unit_delta,
                    "execution_unit_price": execution_unit_price,
                    "trade_notional": trade_notional,
                    "transaction_cost": transaction_cost,
                    "slippage_cost": 0.0,
                }
            )

        equity_rows.append(
            {
                "date": execution_date,
                "signal_date": signal_date,
                "target_weight": target_weight,
                "units": units,
                "cash": cash,
                "unit_price": execution_unit_price,
                "equity": equity,
                "net_return": net_return,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
                "slippage_cost": 0.0,
            }
        )

        total_fee += transaction_cost
        total_turnover += turnover
        previous_equity = equity

    equity_curve = pd.DataFrame(equity_rows)
    trade_log = pd.DataFrame(
        trade_rows,
        columns=[
            "signal_date",
            "execution_date",
            "target_weight",
            "unit_delta",
            "execution_unit_price",
            "trade_notional",
            "transaction_cost",
            "slippage_cost",
        ],
    )
    metrics = calculate_backtest_metrics(
        equity_curve,
        initial_capital=config.initial_capital,
        periods_per_year=config.periods_per_year,
        total_transaction_cost=total_fee,
        total_slippage_cost=0.0,
        total_turnover=total_turnover,
    )

    return BacktestResult(
        equity_curve=equity_curve,
        trade_log=trade_log,
        metrics=metrics,
        market="TEFAS",
        execution_costs=ExecutionCostConfig(
            transaction_cost_bps=config.transaction_cost_bps,
            slippage_bps=0.0,
        ),
    )
