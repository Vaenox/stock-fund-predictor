from __future__ import annotations

import argparse

import pandas as pd

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_stock_indicators
from app.analysis.scoring import calculate_stock_technical_score
from app.backtesting.engine import BacktestConfig, ExecutionCostConfig
from app.backtesting.strategy import SignalScoreWeightConfig, run_signal_score_backtest
from app.ml.risk_adjustment import calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_backtest_real import (
    _buy_and_hold_total_return,
    _load_stock,
    _select_candidate,
    _safe_auc,
    _safe_pr,
)


DEFAULT_SYMBOLS = ("THYAO", "ASELS", "TUPRS", "BIMAS")


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    transaction_cost_bps: float,
    slippage_bps: float,
    max_weight: float,
    min_db_rows: int,
) -> list[dict[str, float | int | str]]:
    raw, source = _load_stock(symbol, days, min_db_rows)
    raw["trading_date"] = pd.to_datetime(raw["trading_date"], errors="raise")
    if raw["trading_date"].duplicated().any():
        raise ValueError("historical stock data contains duplicate trading dates")
    raw = raw.sort_values("trading_date").reset_index(drop=True)

    indicators = calculate_stock_indicators(raw)
    technical = calculate_stock_technical_score(indicators)
    dataset = build_ml_feature_dataset(
        indicators,
        asset_type="stock",
        config=MLFeatureConfig(horizon=5, positive_return_threshold=0.03),
    )

    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )

    technical_lookup = technical.copy()
    technical_lookup["trading_date"] = pd.to_datetime(
        technical_lookup["trading_date"],
        errors="raise",
    )
    technical_lookup = technical_lookup.set_index("trading_date")
    if technical_lookup.index.has_duplicates:
        raise ValueError("technical score data contains duplicate trading dates")

    market_lookup = raw.set_index("trading_date").sort_index()
    if market_lookup.index.has_duplicates:
        raise ValueError("market OHLCV data contains duplicate trading dates")

    ml_columns = list(feature_columns("stock"))
    backtest_config = BacktestConfig(
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
        market_costs={
            "BIST": ExecutionCostConfig(
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
            )
        },
    )
    score_config = SignalScoreWeightConfig(maximum_weight=max_weight)

    results: list[dict[str, float | int | str]] = []

    print("=" * 88)
    print(f"Symbol: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(f"OOS protocol: 3 x 40 test observations | gap={gap} | target=h5/+3%")
    print("-" * 88)

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        candidate = _select_candidate(train, "stock")
        model = fit_baseline_model(
            train,
            asset_type="stock",
            config=candidate.config,
        )
        probability = model.predict_proba(test[ml_columns])[:, 1]

        fold_rows: list[dict[str, float | int | pd.Timestamp]] = []
        for index, (_, test_row) in enumerate(test.iterrows()):
            signal_date = pd.Timestamp(test_row["trading_date"])
            if signal_date not in technical_lookup.index:
                raise ValueError(
                    f"missing technical score for OOS date {signal_date.date()}"
                )
            if signal_date not in market_lookup.index:
                raise ValueError(
                    f"missing market OHLCV for OOS date {signal_date.date()}"
                )

            latest = technical_lookup.loc[signal_date]
            market_row = market_lookup.loc[signal_date]
            risk = calculate_stock_risk_adjustment(latest)
            final_signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                float(risk.adjustment),
            )
            fold_rows.append(
                {
                    "date": signal_date,
                    "open": float(market_row["open"]),
                    "close": float(market_row["close"]),
                    "signal_score": float(final_signal.signal_score),
                    "target": int(test_row["target"]),
                }
            )

        fold_frame = pd.DataFrame(fold_rows)
        signal_result = run_signal_score_backtest(
            fold_frame,
            backtest_config=backtest_config,
            market="BIST",
            score_weight_config=score_config,
        )
        metrics = signal_result.backtest.metrics

        benchmark_return, benchmark_fee, benchmark_slippage, benchmark_cash = (
            _buy_and_hold_total_return(fold_frame, config=backtest_config)
        )
        costless_return, _, _, costless_cash = _buy_and_hold_total_return(
            fold_frame,
            config=BacktestConfig(
                initial_capital=backtest_config.initial_capital,
                transaction_cost_bps=0.0,
                slippage_bps=0.0,
            ),
        )

        auc = _safe_auc(
            fold_frame["target"],
            fold_frame["signal_score"],
        )
        pr = _safe_pr(
            fold_frame["target"],
            fold_frame["signal_score"],
        )
        excess = metrics.total_return - benchmark_return

        print(
            f"Fold {fold_number}: "
            f"signal ROC={auc if auc is not None else float('nan'):.4f} | "
            f"signal PR={pr:.4f}"
        )
        print(
            f"  Strategy={metrics.total_return:+.4%} | "
            f"B&H={benchmark_return:+.4%} | "
            f"Excess={excess:+.4%} | "
            f"Sharpe={metrics.sharpe_ratio:+.3f} | "
            f"MaxDD={metrics.maximum_drawdown:+.4%}"
        )
        print(
            f"  PF={metrics.profit_factor:.4f} | "
            f"Turnover={metrics.total_turnover:.4f} | "
            f"Cost={metrics.total_transaction_cost:.2f} | "
            f"Slippage={metrics.total_slippage_cost:.2f}"
        )
        print(
            f"  Costless B&H={costless_return:+.4%} | "
            f"B&H cost={benchmark_fee + benchmark_slippage:.2f}"
        )

        if benchmark_cash < -1e-8 or costless_cash < -1e-8:
            raise ValueError("buy-and-hold benchmark produced negative cash")

        results.append(
            {
                "symbol": symbol,
                "fold": fold_number,
                "strategy_return": metrics.total_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess,
                "sharpe": metrics.sharpe_ratio,
                "max_drawdown": metrics.maximum_drawdown,
                "profit_factor": metrics.profit_factor,
                "turnover": metrics.total_turnover,
                "transaction_cost": metrics.total_transaction_cost,
                "slippage_cost": metrics.total_slippage_cost,
            }
        )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 6 real backtest comparison across stock symbols."
    )
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated BIST symbols.",
    )
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--max-weight", type=float, default=1.0)
    parser.add_argument("--min-db-rows", type=int, default=400)
    args = parser.parse_args()

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )
    if not symbols:
        raise ValueError("at least one symbol is required")

    all_results: list[dict[str, float | int | str]] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            all_results.extend(
                _run_symbol(
                    symbol,
                    days=args.days,
                    gap=args.gap,
                    transaction_cost_bps=args.transaction_cost_bps,
                    slippage_bps=args.slippage_bps,
                    max_weight=args.max_weight,
                    min_db_rows=args.min_db_rows,
                )
            )
        except Exception as exc:
            failures.append((symbol, str(exc)))
            print("=" * 88)
            print(f"FAILED {symbol}: {exc}")

    if all_results:
        frame = pd.DataFrame(all_results)
        print("=" * 88)
        print("CROSS-SYMBOL SUMMARY")
        print(f"Successful symbols: {frame['symbol'].nunique()}")
        print(f"Successful folds: {len(frame)}")
        print(
            f"Mean strategy return per fold: "
            f"{frame['strategy_return'].mean():+.4%}"
        )
        print(
            f"Mean buy-and-hold return per fold: "
            f"{frame['benchmark_return'].mean():+.4%}"
        )
        print(
            f"Mean strategy excess return per fold: "
            f"{frame['excess_return'].mean():+.4%}"
        )
        print(
            f"Median strategy excess return per fold: "
            f"{frame['excess_return'].median():+.4%}"
        )
        print(
            f"Positive excess-return fold rate: "
            f"{(frame['excess_return'] > 0).mean():.2%}"
        )
        print(f"Mean Sharpe: {frame['sharpe'].mean():+.3f}")
        print(f"Mean max drawdown: {frame['max_drawdown'].mean():+.4%}")
        print(f"Mean turnover: {frame['turnover'].mean():.4f}")
        print()
        print(
            frame[
                [
                    "symbol",
                    "fold",
                    "strategy_return",
                    "benchmark_return",
                    "excess_return",
                    "sharpe",
                    "max_drawdown",
                    "profit_factor",
                ]
            ].to_string(index=False)
        )

    if failures:
        print("=" * 88)
        print("FAILURES")
        for symbol, error in failures:
            print(f"{symbol}: {error}")
        return 1

    if len(all_results) != len(symbols) * 3:
        print("ERROR: not all requested folds completed")
        return 1

    print("=" * 88)
    print("REAL MULTI-STOCK BACKTEST SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
