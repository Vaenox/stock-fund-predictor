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

from smoke_test_backtest_real import _buy_and_hold_total_return, _load_stock, _select_candidate


POLICIES = SUPPORTED_EXPOSURE_MAPPINGS


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
            raise ValueError(f"missing technical score for OOS date {signal_date.date()}")
        if signal_date not in market_lookup.index:
            raise ValueError(f"missing market OHLCV for OOS date {signal_date.date()}")

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


def _select_mapping_policy(
    outer_train: pd.DataFrame,
    *,
    technical_lookup: pd.DataFrame,
    market_lookup: pd.DataFrame,
    backtest_config: BacktestConfig,
    capped_weight: float,
) -> tuple[str, pd.DataFrame]:
    # This is deliberately nested one level inside the outer fold. The model
    # used to score a mapping is fitted only on each inner-training slice.
    tuning_config = TuningConfig(n_inner_splits=2, inner_test_size=20, gap=5)
    inner_folds = build_inner_splits(len(outer_train), config=tuning_config)
    records: list[dict[str, float | int | str]] = []

    for inner_number, fold in enumerate(inner_folds, start=1):
        inner_train = outer_train.iloc[fold.train_start : fold.train_end].copy()
        validation = outer_train.iloc[fold.test_start : fold.test_end].copy()
        try:
            candidate = _select_candidate(inner_train, "stock")
            model = fit_baseline_model(
                inner_train,
                asset_type="stock",
                config=candidate.config,
            )
            signal_frame = _build_signal_frame(
                validation,
                model,
                technical_lookup=technical_lookup,
                market_lookup=market_lookup,
            )
        except ValueError as exc:
            print(
                f"    Inner fold {inner_number}: skipped for mapping selection ({exc})"
            )
            continue

        for policy in POLICIES:
            result = _evaluate_policy(
                signal_frame,
                policy=policy,
                backtest_config=backtest_config,
                capped_weight=capped_weight,
            )
            result["inner_fold"] = inner_number
            records.append(result)

    if not records:
        raise ValueError("no valid inner fold available for mapping selection")

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
    summary["selected"] = summary["policy"].eq(selected)
    return selected, summary


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    transaction_cost_bps: float,
    slippage_bps: float,
    capped_weight: float,
    min_db_rows: int,
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float | int | str]]]:
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

    all_outer: list[dict[str, float | int | str]] = []
    selected_outer: list[dict[str, float | int | str]] = []

    print("=" * 96)
    print(f"Symbol: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(
        "Nested mapping protocol: outer 3 x 40 | gap=5 | "
        "inner 2 x 20 | target=h5/+3%"
    )
    print("-" * 96)

    for fold_number, fold in enumerate(folds, start=1):
        outer_train = dataset.iloc[fold.train_start : fold.train_end].copy()
        outer_test = dataset.iloc[fold.test_start : fold.test_end].copy()

        selected_policy, inner_summary = _select_mapping_policy(
            outer_train,
            technical_lookup=technical_lookup,
            market_lookup=market_lookup,
            backtest_config=backtest_config,
            capped_weight=capped_weight,
        )

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

        print(
            f"Fold {fold_number}: selected mapping={selected_policy} | "
            f"inner mean excess={float(inner_summary.iloc[0]['mean_excess_return']):+.4%}"
        )
        print("  Inner ranking:")
        for _, item in inner_summary.iterrows():
            print(
                f"    {item['policy']:<8} "
                f"excess={float(item['mean_excess_return']):+.4%} | "
                f"Sharpe={float(item['mean_sharpe']):+.3f} | "
                f"MaxDD={float(item['mean_max_drawdown']):+.4%} | "
                f"turnover={float(item['mean_turnover']):.4f} | "
                f"folds={int(item['valid_inner_folds'])}"
            )

        for policy in POLICIES:
            result = _evaluate_policy(
                outer_signal,
                policy=policy,
                backtest_config=backtest_config,
                capped_weight=capped_weight,
            )
            result.update({"symbol": symbol, "fold": fold_number})
            all_outer.append(result)

            if policy == selected_policy:
                selected_outer.append(result)

            print(
                f"  OOS {policy:<8} "
                f"Strategy={float(result['strategy_return']):+.4%} | "
                f"B&H={float(result['benchmark_return']):+.4%} | "
                f"Excess={float(result['excess_return']):+.4%} | "
                f"Sharpe={float(result['sharpe']):+.3f} | "
                f"MaxDD={float(result['max_drawdown']):+.4%}"
            )

    return all_outer, selected_outer


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nested real-data sensitivity test for signal-score exposure mappings."
    )
    parser.add_argument(
        "--symbols",
        default="THYAO,ASELS,TUPRS,BIMAS",
        help="Comma-separated BIST symbols.",
    )
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
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

    all_outer: list[dict[str, float | int | str]] = []
    selected_outer: list[dict[str, float | int | str]] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            outer, selected = _run_symbol(
                symbol,
                days=args.days,
                gap=args.gap,
                transaction_cost_bps=args.transaction_cost_bps,
                slippage_bps=args.slippage_bps,
                capped_weight=args.capped_weight,
                min_db_rows=args.min_db_rows,
            )
            all_outer.extend(outer)
            selected_outer.extend(selected)
        except Exception as exc:
            failures.append((symbol, str(exc)))
            print("=" * 96)
            print(f"FAILED {symbol}: {exc}")

    if all_outer:
        frame = pd.DataFrame(all_outer)
        selected = pd.DataFrame(selected_outer)

        print("=" * 96)
        print("MAPPING SENSITIVITY SUMMARY")
        print(f"Successful symbols: {frame['symbol'].nunique()}")
        print(
            "Successful outer folds: "
            f"{frame[['symbol', 'fold']].drop_duplicates().shape[0]}"
        )
        print()
        print("All-policy outer OOS:")
        policy_summary = (
            frame.groupby("policy", as_index=False)
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
            .sort_values("mean_excess_return", ascending=False)
        )
        print(policy_summary.to_string(index=False))

        if not selected.empty:
            print()
            print("Nested-selected outer OOS:")
            selected_summary = (
                selected.groupby("symbol", as_index=False)
                .agg(
                    mean_strategy_return=("strategy_return", "mean"),
                    mean_benchmark_return=("benchmark_return", "mean"),
                    mean_excess_return=("excess_return", "mean"),
                    positive_excess_rate=(
                        "excess_return",
                        lambda series: float((series > 0).mean()),
                    ),
                    mean_sharpe=("sharpe", "mean"),
                    mean_max_drawdown=("max_drawdown", "mean"),
                    mean_turnover=("turnover", "mean"),
                )
            )
            print(selected_summary.to_string(index=False))

            print()
            print("Nested-selected policy frequency:")
            print(
                selected.groupby(["symbol", "policy"])
                .size()
                .rename("selected_outer_folds")
                .reset_index()
                .to_string(index=False)
            )

            print()
            print("Nested-selected aggregate OOS:")
            print(
                f"Mean strategy return: {selected['strategy_return'].mean():+.4%}"
            )
            print(
                f"Mean B&H return: {selected['benchmark_return'].mean():+.4%}"
            )
            print(
                f"Mean excess return: {selected['excess_return'].mean():+.4%}"
            )
            print(
                f"Median excess return: {selected['excess_return'].median():+.4%}"
            )
            print(
                "Positive excess fold rate: "
                f"{(selected['excess_return'] > 0).mean():.2%}"
            )
            print(f"Mean Sharpe: {selected['sharpe'].mean():+.3f}")
            print(f"Mean max drawdown: {selected['max_drawdown'].mean():+.4%}")
            print(f"Mean turnover: {selected['turnover'].mean():.4f}")

    if failures:
        print("=" * 96)
        print("FAILURES")
        for symbol, error in failures:
            print(f"{symbol}: {error}")
        return 1

    expected = len(symbols) * 3 * len(POLICIES)
    if len(all_outer) != expected:
        print(f"ERROR: expected {expected} outer-policy rows, got {len(all_outer)}")
        return 1

    if len(selected_outer) != len(symbols) * 3:
        print(
            "ERROR: every successful outer fold must produce exactly one "
            "nested-selected policy"
        )
        return 1

    print("=" * 96)
    print("REAL NESTED MAPPING SENSITIVITY SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
