from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators
from app.analysis.scoring import calculate_fund_technical_score
from app.backtesting.fund_engine import (
    FundBacktestConfig,
    calculate_fund_buy_and_hold_total_return,
    run_long_only_fund_backtest,
)
from app.backtesting.strategy import SignalScoreWeightConfig, map_signal_scores_to_target_weights
from app.core.settings import get_settings
from app.ml.risk_adjustment import calculate_fund_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_backtest_fund_real import _load_fund, _select_best_candidate_sparse


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    min_db_rows: int,
    threshold: float,
    transaction_cost_bps: float,
    max_weight: float,
    chunk_delay: float,
) -> list[dict[str, float | int | str]]:
    raw, source = _load_fund(symbol, days, min_db_rows, chunk_delay)
    raw["pricing_date"] = pd.to_datetime(raw["pricing_date"], errors="raise")
    if raw["pricing_date"].duplicated().any():
        raise ValueError("historical fund data contains duplicate pricing dates")
    raw = raw.sort_values("pricing_date").reset_index(drop=True)

    indicators = calculate_fund_indicators(raw)
    technical = calculate_fund_technical_score(indicators)
    dataset = build_ml_feature_dataset(
        indicators,
        asset_type="fund",
        config=MLFeatureConfig(
            horizon=5,
            positive_return_threshold=threshold,
        ),
    )
    if len(dataset) <= 3 * 40 + gap:
        raise ValueError(
            f"not enough dataset observations for 3x40 outer OOS with gap={gap}: "
            f"got {len(dataset)}"
        )

    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    technical_lookup = technical.copy()
    technical_lookup["pricing_date"] = pd.to_datetime(
        technical_lookup["pricing_date"],
        errors="raise",
    )
    technical_lookup = technical_lookup.set_index("pricing_date")
    price_lookup = raw.set_index("pricing_date").sort_index()

    columns = list(feature_columns("fund"))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )
    backtest_config = FundBacktestConfig(
        transaction_cost_bps=transaction_cost_bps,
    )
    score_config = SignalScoreWeightConfig(maximum_weight=max_weight)
    results: list[dict[str, float | int | str]] = []

    print("=" * 96)
    print(f"Fund: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(
        f"Protocol: 3 x 40 OOS | gap={gap} | h5/{threshold:.2%} | "
        f"transaction_cost={transaction_cost_bps:.2f} bps"
    )
    print("Ablation: production risk adjustment vs risk adjustment = 0")
    print("-" * 96)

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        tuning = _select_best_candidate_sparse(
            train,
            asset_type="fund",
            tuning_config=tuning_config,
        )
        model = fit_baseline_model(
            train,
            asset_type="fund",
            config=tuning.config,
        )
        probability = model.predict_proba(test[columns])[:, 1]

        production_rows: list[dict[str, object]] = []
        no_risk_rows: list[dict[str, object]] = []
        risk_scores: list[float] = []
        risk_adjustments: list[float] = []

        for index, (_, test_row) in enumerate(test.iterrows()):
            signal_date = pd.Timestamp(test_row["pricing_date"])
            latest = technical_lookup.loc[signal_date]
            unit_price = float(price_lookup.loc[signal_date]["unit_price"])

            risk = calculate_fund_risk_adjustment(latest)
            production_signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                risk.adjustment,
            )
            no_risk_signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                0.0,
            )

            production_weight = float(
                map_signal_scores_to_target_weights(
                    pd.Series([production_signal.signal_score]),
                    config=score_config,
                    policy="linear",
                ).iloc[0]
            )
            no_risk_weight = float(
                map_signal_scores_to_target_weights(
                    pd.Series([no_risk_signal.signal_score]),
                    config=score_config,
                    policy="linear",
                ).iloc[0]
            )

            common = {
                "date": signal_date,
                "unit_price": unit_price,
                "target": int(test_row["target"]),
                "forward_return_5d": float(test_row["forward_return_5d"]),
                "ml_probability": float(probability[index]),
                "technical_score": float(latest["technical_score"]),
                "risk_score": float(risk.risk_score),
                "risk_adjustment": float(risk.adjustment),
            }

            production_rows.append(
                {
                    **common,
                    "signal_score": float(production_signal.signal_score),
                    "target_weight": production_weight,
                }
            )
            no_risk_rows.append(
                {
                    **common,
                    "signal_score": float(no_risk_signal.signal_score),
                    "target_weight": no_risk_weight,
                }
            )
            risk_scores.append(float(risk.risk_score))
            risk_adjustments.append(float(risk.adjustment))

        production_frame = pd.DataFrame(production_rows)
        no_risk_frame = pd.DataFrame(no_risk_rows)

        production = run_long_only_fund_backtest(
            production_frame,
            config=backtest_config,
        )
        no_risk = run_long_only_fund_backtest(
            no_risk_frame,
            config=backtest_config,
        )
        benchmark_return, _, _ = calculate_fund_buy_and_hold_total_return(
            production_frame,
            config=backtest_config,
        )

        results.append(
            {
                "symbol": symbol,
                "fold": fold_number,
                "production_return": production.metrics.total_return,
                "no_risk_return": no_risk.metrics.total_return,
                "benchmark_return": benchmark_return,
                "production_excess": production.metrics.total_return - benchmark_return,
                "no_risk_excess": no_risk.metrics.total_return - benchmark_return,
                "risk_delta_return": production.metrics.total_return - no_risk.metrics.total_return,
                "production_turnover": production.metrics.total_turnover,
                "no_risk_turnover": no_risk.metrics.total_turnover,
                "risk_mean": float(np.mean(risk_scores)),
                "risk_adjustment_mean": float(np.mean(risk_adjustments)),
                "inner_pr_auc": float(tuning.score),
            }
        )

        print(f"Fold {fold_number}: inner PR-AUC={tuning.score:.4f}")
        print(
            f"  Mean risk score={np.mean(risk_scores):.4f} | "
            f"Mean adjustment={np.mean(risk_adjustments):+.4f}"
        )
        print(
            f"  Production: {production.metrics.total_return:+.4%} "
            f"(excess {production.metrics.total_return - benchmark_return:+.4%}) | "
            f"turnover={production.metrics.total_turnover:.4f}"
        )
        print(
            f"  No-risk:    {no_risk.metrics.total_return:+.4%} "
            f"(excess {no_risk.metrics.total_return - benchmark_return:+.4%}) | "
            f"turnover={no_risk.metrics.total_turnover:.4f}"
        )
        print(
            f"  Risk contribution to return: "
            f"{production.metrics.total_return - no_risk.metrics.total_return:+.4%}"
        )

        if len(production.equity_curve) != 39 or len(no_risk.equity_curve) != 39:
            raise AssertionError("each OOS fold must produce 39 executable periods")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a real-fund OOS ablation comparing production risk vs no-risk signals."
    )
    parser.add_argument("--symbols", default="AFA,AFT")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--max-weight", type=float, default=1.0)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )
    if not symbols:
        raise SystemExit("symbols cannot be empty")
    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")
    if args.threshold <= -1.0:
        raise SystemExit("threshold must be greater than -1")
    if args.transaction_cost_bps < 0:
        raise SystemExit("transaction-cost-bps cannot be negative")
    if not 0.0 < args.max_weight <= 1.0:
        raise SystemExit("max-weight must be between 0 and 1")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    all_results: list[dict[str, float | int | str]] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            all_results.extend(
                _run_symbol(
                    symbol,
                    days=args.days,
                    gap=args.gap,
                    min_db_rows=args.min_db_rows,
                    threshold=args.threshold,
                    transaction_cost_bps=args.transaction_cost_bps,
                    max_weight=args.max_weight,
                    chunk_delay=args.chunk_delay,
                )
            )
        except Exception as exc:
            failures.append((symbol, f"{type(exc).__name__}: {exc}"))
            print("=" * 96)
            print(f"FAILED {symbol}: {type(exc).__name__}: {exc}")

    if failures:
        print("=" * 96)
        print("FAILURES")
        for symbol, message in failures:
            print(f"{symbol}: {message}")
        return 1

    frame = pd.DataFrame(all_results)
    print("=" * 96)
    print("CROSS-FUND RISK ABLATION SUMMARY")
    print(f"Folds: {len(frame)}")
    print(f"Mean production return: {frame['production_return'].mean():+.4%}")
    print(f"Mean no-risk return: {frame['no_risk_return'].mean():+.4%}")
    print(f"Mean B&H: {frame['benchmark_return'].mean():+.4%}")
    print(f"Mean production excess: {frame['production_excess'].mean():+.4%}")
    print(f"Mean no-risk excess: {frame['no_risk_excess'].mean():+.4%}")
    print(f"Mean risk contribution: {frame['risk_delta_return'].mean():+.4%}")
    print(
        f"Risk helps folds: {(frame['risk_delta_return'] > 0).sum()}/"
        f"{len(frame)}"
    )
    print(f"Mean production turnover: {frame['production_turnover'].mean():.4f}")
    print(f"Mean no-risk turnover: {frame['no_risk_turnover'].mean():.4f}")
    print(f"Mean risk score: {frame['risk_mean'].mean():.4f}")
    print(f"Mean risk adjustment: {frame['risk_adjustment_mean'].mean():+.4f}")

    assert len(frame) == len(symbols) * 3
    assert np.isfinite(
        frame[
            [
                "production_return",
                "no_risk_return",
                "benchmark_return",
                "risk_delta_return",
                "risk_mean",
                "risk_adjustment_mean",
            ]
        ].to_numpy(dtype=float)
    ).all()
    print("REAL FUND RISK ABLATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
