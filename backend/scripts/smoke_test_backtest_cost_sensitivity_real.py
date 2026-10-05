from __future__ import annotations

import argparse

import pandas as pd

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_stock_indicators
from app.analysis.scoring import calculate_stock_technical_score
from app.backtesting.engine import BacktestConfig, ExecutionCostConfig
from app.backtesting.strategy import (
    SUPPORTED_EXPOSURE_MAPPINGS,
    SignalScoreWeightConfig,
    run_signal_score_backtest,
)
from app.ml.risk_adjustment import calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, build_inner_splits
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_backtest_real import (
    _buy_and_hold_total_return,
    _load_stock,
    _select_candidate,
)


POLICIES = SUPPORTED_EXPOSURE_MAPPINGS
DEFAULT_COST_GRID = ((0.0, 0.0), (5.0, 2.5), (10.0, 5.0), (20.0, 10.0))


def _parse_cost_grid(value: str) -> tuple[tuple[float, float], ...]:
    scenarios: list[tuple[float, float]] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 2:
            raise ValueError(
                "cost grid entries must use transaction_bps:slippage_bps"
            )
        transaction = float(parts[0])
        slippage = float(parts[1])
        if transaction < 0.0 or slippage < 0.0:
            raise ValueError("cost grid values cannot be negative")
        scenarios.append((transaction, slippage))
    if not scenarios:
        raise ValueError("at least one cost scenario is required")
    return tuple(scenarios)


def _config_for_cost(
    transaction_cost_bps: float,
    slippage_bps: float,
) -> BacktestConfig:
    return BacktestConfig(
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=slippage_bps,
        market_costs={
            "BIST": ExecutionCostConfig(
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
            )
        },
    )


def _build_signal_frame(
    rows: pd.DataFrame,
    model,
    *,
    technical_lookup: pd.DataFrame,
    market_lookup: pd.DataFrame,
) -> pd.DataFrame:
    columns = list(feature_columns("stock"))
    probability = model.predict_proba(rows[columns])[:, 1]
    output: list[dict[str, float | int | pd.Timestamp]] = []

    for index, (_, row) in enumerate(rows.iterrows()):
        signal_date = pd.Timestamp(row["trading_date"])
        if signal_date not in technical_lookup.index:
            raise ValueError(f"missing technical score for {signal_date.date()}")
        if signal_date not in market_lookup.index:
            raise ValueError(f"missing market OHLCV for {signal_date.date()}")

        latest = technical_lookup.loc[signal_date]
        market_row = market_lookup.loc[signal_date]
        risk = calculate_stock_risk_adjustment(latest)
        signal = calculate_signal_score(
            float(probability[index]),
            float(latest["technical_score"]),
            float(risk.adjustment),
        )
        output.append(
            {
                "date": signal_date,
                "open": float(market_row["open"]),
                "close": float(market_row["close"]),
                "signal_score": float(signal.signal_score),
                "target": int(row["target"]),
            }
        )
    return pd.DataFrame(output)


def _evaluate_policy(
    signal_frame: pd.DataFrame,
    *,
    policy: str,
    backtest_config: BacktestConfig,
    capped_weight: float,
) -> dict[str, float | str]:
    result = run_signal_score_backtest(
        signal_frame,
        backtest_config=backtest_config,
        market="BIST",
        score_weight_config=SignalScoreWeightConfig(maximum_weight=1.0),
        mapping_policy=policy,
        capped_weight=capped_weight,
    )
    benchmark_return, _, _, _ = _buy_and_hold_total_return(
        signal_frame,
        config=backtest_config,
    )
    metrics = result.backtest.metrics
    return {
        "policy": policy,
        "strategy_return": metrics.total_return,
        "benchmark_return": benchmark_return,
        "excess_return": metrics.total_return - benchmark_return,
        "sharpe": metrics.sharpe_ratio,
        "max_drawdown": metrics.maximum_drawdown,
        "turnover": metrics.total_turnover,
    }


def _select_policy_from_inner_frames(
    inner_frames: list[pd.DataFrame],
    *,
    backtest_config: BacktestConfig,
    capped_weight: float,
) -> tuple[str, pd.DataFrame]:
    records: list[dict[str, float | int | str]] = []

    for inner_number, signal_frame in enumerate(inner_frames, start=1):
        for policy in POLICIES:
            result = _evaluate_policy(
                signal_frame,
                policy=policy,
                backtest_config=backtest_config,
                capped_weight=capped_weight,
            )
            result["inner_fold"] = inner_number
            records.append(result)

    frame = pd.DataFrame(records)
    counts = frame.groupby("policy")["inner_fold"].nunique()
    eligible = [policy for policy in POLICIES if int(counts.get(policy, 0)) >= 2]
    if not eligible:
        raise ValueError(
            "mapping selection requires two valid inner folds; "
            f"got counts={counts.to_dict()}"
        )

    summary = (
        frame[frame["policy"].isin(eligible)]
        .groupby("policy", as_index=False)
        .agg(
            mean_excess_return=("excess_return", "mean"),
            median_excess_return=("excess_return", "median"),
            mean_sharpe=("sharpe", "mean"),
            mean_max_drawdown=("max_drawdown", "mean"),
            mean_turnover=("turnover", "mean"),
            valid_inner_folds=("inner_fold", "nunique"),
        )
    )
    policy_order = {policy: index for index, policy in enumerate(POLICIES)}
    summary["policy_order"] = summary["policy"].map(policy_order)
    summary = summary.sort_values(
        [
            "mean_excess_return",
            "median_excess_return",
            "mean_sharpe",
            "mean_max_drawdown",
            "mean_turnover",
            "policy_order",
        ],
        ascending=[False, False, False, False, True, True],
    ).reset_index(drop=True)
    selected = str(summary.iloc[0]["policy"])
    return selected, summary


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    cost_grid: tuple[tuple[float, float], ...],
    capped_weight: float,
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
        technical_lookup["trading_date"], errors="raise"
    )
    technical_lookup = technical_lookup.set_index("trading_date")
    if technical_lookup.index.has_duplicates:
        raise ValueError("technical score data contains duplicate trading dates")

    market_lookup = raw.set_index("trading_date").sort_index()
    if market_lookup.index.has_duplicates:
        raise ValueError("market OHLCV data contains duplicate trading dates")

    # Models/signals are independent of execution cost, so build them once and
    # reuse the exact same inner/outer signal frames for every cost scenario.
    tuning_config = TuningConfig(n_inner_splits=2, inner_test_size=20, gap=gap)
    cost_results: list[dict[str, float | int | str]] = []

    print("=" * 96)
    print(f"Symbol: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(
        "Cost sensitivity protocol: outer 3 x 40 | gap=5 | "
        "inner 2 x 20 | target=h5/+3%"
    )
    print("-" * 96)

    for fold_number, fold in enumerate(folds, start=1):
        outer_train = dataset.iloc[fold.train_start : fold.train_end].copy()
        outer_test = dataset.iloc[fold.test_start : fold.test_end].copy()

        inner_frames: list[pd.DataFrame] = []
        inner_folds = build_inner_splits(len(outer_train), config=tuning_config)

        for inner_number, inner_fold in enumerate(inner_folds, start=1):
            inner_train = outer_train.iloc[
                inner_fold.train_start : inner_fold.train_end
            ].copy()
            validation = outer_train.iloc[
                inner_fold.test_start : inner_fold.test_end
            ].copy()
            try:
                candidate = _select_candidate(inner_train, "stock")
                model = fit_baseline_model(
                    inner_train,
                    asset_type="stock",
                    config=candidate.config,
                )
                inner_frames.append(
                    _build_signal_frame(
                        validation,
                        model,
                        technical_lookup=technical_lookup,
                        market_lookup=market_lookup,
                    )
                )
            except ValueError as exc:
                print(f"  Inner fold {inner_number}: skipped ({exc})")

        outer_candidate = _select_candidate(outer_train, "stock")
        outer_model = fit_baseline_model(
            outer_train,
            asset_type="stock",
            config=outer_candidate.config,
        )
        outer_signal = _build_signal_frame(
            outer_test,
            outer_model,
            technical_lookup=technical_lookup,
            market_lookup=market_lookup,
        )

        for transaction_cost_bps, slippage_bps in cost_grid:
            cost_label = f"{transaction_cost_bps:g}/{slippage_bps:g}"
            backtest_config = _config_for_cost(
                transaction_cost_bps,
                slippage_bps,
            )
            selected_policy, inner_summary = _select_policy_from_inner_frames(
                inner_frames,
                backtest_config=backtest_config,
                capped_weight=capped_weight,
            )
            selected_inner_excess = float(
                inner_summary.iloc[0]["mean_excess_return"]
            )

            print(
                f"Fold {fold_number} | cost={cost_label} bps "
                f"tx/slip | selected={selected_policy} | "
                f"inner excess={selected_inner_excess:+.4%}"
            )

            for policy in POLICIES:
                result = _evaluate_policy(
                    outer_signal,
                    policy=policy,
                    backtest_config=backtest_config,
                    capped_weight=capped_weight,
                )
                result.update(
                    {
                        "symbol": symbol,
                        "fold": fold_number,
                        "cost_transaction_bps": transaction_cost_bps,
                        "cost_slippage_bps": slippage_bps,
                        "selected": policy == selected_policy,
                    }
                )
                cost_results.append(result)
                print(
                    f"  OOS {policy:<8} "
                    f"Strategy={float(result['strategy_return']):+.4%} | "
                    f"B&H={float(result['benchmark_return']):+.4%} | "
                    f"Excess={float(result['excess_return']):+.4%} | "
                    f"Sharpe={float(result['sharpe']):+.3f} | "
                    f"Turnover={float(result['turnover']):.4f}"
                )

    return cost_results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nested execution-cost sensitivity for signal-score exposure mappings."
    )
    parser.add_argument(
        "--symbols",
        default="THYAO,ASELS,TUPRS,BIMAS,KCHOL,SAHOL,SISE,EREGL",
        help="Comma-separated BIST symbols.",
    )
    parser.add_argument("--days", type=int, default=2000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument(
        "--cost-grid",
        default=",".join(f"{tx}:{slip}" for tx, slip in DEFAULT_COST_GRID),
        help="Comma-separated transaction_bps:slippage_bps scenarios.",
    )
    parser.add_argument("--capped-weight", type=float, default=0.75)
    parser.add_argument("--min-db-rows", type=int, default=400)
    args = parser.parse_args()

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )
    if not symbols:
        raise ValueError("at least one symbol is required")
    cost_grid = _parse_cost_grid(args.cost_grid)

    all_results: list[dict[str, float | int | str]] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            all_results.extend(
                _run_symbol(
                    symbol,
                    days=args.days,
                    gap=args.gap,
                    cost_grid=cost_grid,
                    capped_weight=args.capped_weight,
                    min_db_rows=args.min_db_rows,
                )
            )
        except Exception as exc:
            failures.append((symbol, str(exc)))
            print("=" * 96)
            print(f"FAILED {symbol}: {exc}")

    if all_results:
        frame = pd.DataFrame(all_results)
        print("=" * 96)
        print("EXECUTION-COST SENSITIVITY SUMMARY")
        print(f"Successful symbols: {frame['symbol'].nunique()}")
        print(f"Successful outer folds: {frame[['symbol', 'fold']].drop_duplicates().shape[0]}")
        print()

        grouped = (
            frame.groupby(
                ["cost_transaction_bps", "cost_slippage_bps", "policy"],
                as_index=False,
            )
            .agg(
                mean_strategy_return=("strategy_return", "mean"),
                mean_benchmark_return=("benchmark_return", "mean"),
                mean_excess_return=("excess_return", "mean"),
                median_excess_return=("excess_return", "median"),
                positive_excess_rate=(
                    "excess_return",
                    lambda series: float((series > 0).mean()),
                ),
                mean_sharpe=("sharpe", "mean"),
                mean_max_drawdown=("max_drawdown", "mean"),
                mean_turnover=("turnover", "mean"),
            )
            .sort_values(
                [
                    "cost_transaction_bps",
                    "cost_slippage_bps",
                    "mean_excess_return",
                ],
                ascending=[True, True, False],
            )
        )
        print(grouped.to_string(index=False))

        selected = frame[frame["selected"]].copy()
        print()
        print("NESTED-SELECTED COST SENSITIVITY")
        selected_grouped = (
            selected.groupby(
                ["cost_transaction_bps", "cost_slippage_bps"],
                as_index=False,
            )
            .agg(
                mean_strategy_return=("strategy_return", "mean"),
                mean_benchmark_return=("benchmark_return", "mean"),
                mean_excess_return=("excess_return", "mean"),
                median_excess_return=("excess_return", "median"),
                positive_excess_rate=(
                    "excess_return",
                    lambda series: float((series > 0).mean()),
                ),
                mean_sharpe=("sharpe", "mean"),
                mean_max_drawdown=("max_drawdown", "mean"),
                mean_turnover=("turnover", "mean"),
                selected_policy_folds=("selected", "size"),
            )
            .sort_values(["cost_transaction_bps", "cost_slippage_bps"])
        )
        print(selected_grouped.to_string(index=False))

        print()
        print("NESTED-SELECTED POLICY FREQUENCY BY COST")
        frequency = (
            selected.groupby(
                ["cost_transaction_bps", "cost_slippage_bps", "policy"]
            )
            .size()
            .rename("selected_folds")
            .reset_index()
            .sort_values(
                ["cost_transaction_bps", "cost_slippage_bps", "selected_folds"],
                ascending=[True, True, False],
            )
        )
        print(frequency.to_string(index=False))

    if failures:
        print("=" * 96)
        print("FAILURES")
        for symbol, error in failures:
            print(f"{symbol}: {error}")
        return 1

    expected = len(symbols) * 3 * len(cost_grid) * len(POLICIES)
    if len(all_results) != expected:
        print(f"ERROR: expected {expected} result rows, got {len(all_results)}")
        return 1

    selected = sum(1 for row in all_results if row["selected"])
    if selected != len(symbols) * 3 * len(cost_grid):
        print(
            "ERROR: every symbol/fold/cost scenario must select exactly one "
            "mapping policy"
        )
        return 1

    print("=" * 96)
    print("REAL NESTED EXECUTION-COST SENSITIVITY SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
