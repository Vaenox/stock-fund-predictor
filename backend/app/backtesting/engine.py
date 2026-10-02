from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import BacktestMetrics, calculate_backtest_metrics


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    transaction_cost_bps: float = 10.0
    slippage_bps: float = 5.0
    periods_per_year: int = 252

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps cannot be negative")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps cannot be negative")
        if self.slippage_bps >= 10_000:
            raise ValueError("slippage_bps must be below 10000")
        if self.periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")


@dataclass(frozen=True, slots=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    trade_log: pd.DataFrame
    metrics: BacktestMetrics


_REQUIRED_COLUMNS = {"open", "close", "target_weight"}


def _validate_input(frame: pd.DataFrame, date_column: str, target_column: str) -> pd.DataFrame:
    required = {"open", "close", target_column, date_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("backtest frame is missing columns: " + ", ".join(missing))
    if len(frame) < 2:
        raise ValueError("backtest requires at least two observations")

    result = frame.copy()
    result[date_column] = pd.to_datetime(result[date_column], errors="raise")
    if result[date_column].duplicated().any():
        raise ValueError("backtest dates must be unique")
    result = result.sort_values(date_column).reset_index(drop=True)

    for column in ("open", "close", target_column):
        result[column] = pd.to_numeric(result[column], errors="raise")

    if not np.isfinite(result[["open", "close", target_column]].to_numpy()).all():
        raise ValueError("open, close, and target_weight must be finite")
    if (result[["open", "close"]] <= 0).any().any():
        raise ValueError("open and close must be positive")
    if not result[target_column].between(0.0, 1.0).all():
        raise ValueError("target_weight must be between 0 and 1")

    return result


def run_long_only_backtest(
    frame: pd.DataFrame,
    *,
    config: BacktestConfig | None = None,
    date_column: str = "date",
    target_column: str = "target_weight",
) -> BacktestResult:
    """Run a long-only, next-open execution backtest.

    A target weight observed at date t is executed at date t+1 open.
    This prevents using the next day's close (or later information) to
    execute a signal generated at t.
    """
    config = config or BacktestConfig()
    data = _validate_input(frame, date_column, target_column)

    cash = config.initial_capital
    shares = 0.0
    previous_equity = config.initial_capital

    fee_rate = config.transaction_cost_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0

    equity_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []
    total_fee = 0.0
    total_slippage = 0.0
    total_turnover = 0.0

    for index in range(len(data) - 1):
        signal_row = data.iloc[index]
        execution_row = data.iloc[index + 1]

        signal_date = signal_row[date_column]
        execution_date = execution_row[date_column]
        target_weight = float(signal_row[target_column])

        signal_close = float(signal_row["close"])
        execution_open = float(execution_row["open"])
        execution_close = float(execution_row["close"])

        equity_at_signal = cash + shares * signal_close
        desired_position_value = equity_at_signal * target_weight
        desired_shares = desired_position_value / execution_open
        share_delta = desired_shares - shares

        if share_delta > 0:
            execution_price = execution_open * (1.0 + slippage_rate)
        elif share_delta < 0:
            execution_price = execution_open * (1.0 - slippage_rate)
        else:
            execution_price = execution_open

        trade_notional_at_mid = abs(share_delta) * execution_open
        slippage_cost = abs(share_delta) * abs(execution_price - execution_open)
        transaction_cost = trade_notional_at_mid * fee_rate

        if share_delta > 0:
            cash -= share_delta * execution_price
        elif share_delta < 0:
            cash += (-share_delta) * execution_price

        cash -= transaction_cost
        shares = desired_shares

        equity = cash + shares * execution_close
        net_return = equity / previous_equity - 1.0
        turnover = (
            trade_notional_at_mid / equity_at_signal
            if equity_at_signal > 0
            else 0.0
        )

        if share_delta != 0:
            trade_rows.append(
                {
                    "signal_date": signal_date,
                    "execution_date": execution_date,
                    "target_weight": target_weight,
                    "share_delta": share_delta,
                    "execution_price": execution_price,
                    "trade_notional": trade_notional_at_mid,
                    "transaction_cost": transaction_cost,
                    "slippage_cost": slippage_cost,
                }
            )

        equity_rows.append(
            {
                "date": execution_date,
                "signal_date": signal_date,
                "target_weight": target_weight,
                "shares": shares,
                "cash": cash,
                "equity": equity,
                "net_return": net_return,
                "turnover": turnover,
                "transaction_cost": transaction_cost,
                "slippage_cost": slippage_cost,
            }
        )

        total_fee += transaction_cost
        total_slippage += slippage_cost
        total_turnover += turnover
        previous_equity = equity

    equity_curve = pd.DataFrame(equity_rows)
    trade_log = pd.DataFrame(
        trade_rows,
        columns=[
            "signal_date",
            "execution_date",
            "target_weight",
            "share_delta",
            "execution_price",
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
        total_slippage_cost=total_slippage,
        total_turnover=total_turnover,
    )

    return BacktestResult(
        equity_curve=equity_curve,
        trade_log=trade_log,
        metrics=metrics,
    )
