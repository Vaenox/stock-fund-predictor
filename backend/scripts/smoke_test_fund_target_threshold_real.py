from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators
from app.backtesting.fund_diagnostics import summarize_score_quintiles
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_backtest_fund_real import _load_fund, _select_best_candidate_sparse


def _safe_roc_auc(target: pd.Series, probability: np.ndarray) -> float | None:
    if target.nunique() < 2:
        return None
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(target.astype(int), probability))


def _safe_pr_auc(target: pd.Series, probability: np.ndarray) -> float | None:
    if target.nunique() < 2:
        return None
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(target.astype(int), probability))


def _safe_spearman(left: pd.Series, right: pd.Series) -> float | None:
    if left.nunique() < 2 or right.nunique() < 2:
        return None
    value = left.corr(right, method="spearman")
    return float(value) if pd.notna(value) else None


def _run_threshold(
    symbol: str,
    *,
    raw: pd.DataFrame,
    threshold: float,
    gap: int,
) -> dict[str, float | int | str]:
    indicators = calculate_fund_indicators(raw)
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
            f"not enough dataset observations for threshold {threshold:.2%}: "
            f"{len(dataset)}"
        )

    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    columns = list(feature_columns("fund"))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )

    fold_metrics: list[dict[str, float | int]] = []
    oos_parts: list[pd.DataFrame] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        if train["target"].nunique() < 2:
            raise ValueError(
                f"threshold {threshold:.2%} fold {fold_number} training has one class"
            )

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
        target = test["target"].astype(int).reset_index(drop=True)
        forward_return = test["forward_return_5d"].astype(float).reset_index(drop=True)
        probability_series = pd.Series(probability)

        roc = _safe_roc_auc(target, probability)
        pr = _safe_pr_auc(target, probability)
        spearman = _safe_spearman(probability_series, forward_return)

        quintiles = summarize_score_quintiles(
            pd.DataFrame(
                {
                    "target_weight": probability,
                    "target": target.to_numpy(),
                    "forward_return_5d": forward_return.to_numpy(),
                    "ml_probability": probability,
                    "technical_score": probability,
                    "signal_score": probability,
                }
            ),
            score_column="ml_probability",
        )
        q1 = float(
            quintiles.loc[quintiles["quintile"] == "Q1", "mean_forward_return_5d"].iloc[0]
        )
        q5 = float(
            quintiles.loc[quintiles["quintile"] == "Q5", "mean_forward_return_5d"].iloc[0]
        )

        fold_metrics.append(
            {
                "fold": fold_number,
                "train_positive_rate": float(train["target"].mean()),
                "test_positive_rate": float(test["target"].mean()),
                "inner_pr_auc": float(tuning.score),
                "roc_auc": roc if roc is not None else float("nan"),
                "pr_auc": pr if pr is not None else float("nan"),
                "spearman_forward_return_5d": (
                    spearman if spearman is not None else float("nan")
                ),
                "q1_mean_forward_return_5d": q1,
                "q5_mean_forward_return_5d": q5,
                "q5_minus_q1_forward_return": q5 - q1,
            }
        )
        oos_parts.append(
            pd.DataFrame(
                {
                    "target": target.to_numpy(),
                    "forward_return_5d": forward_return.to_numpy(),
                    "ml_probability": probability,
                }
            )
        )

        print(
            f"  Fold {fold_number}: train target={train['target'].mean():.2%}, "
            f"OOS target={test['target'].mean():.2%}, "
            f"inner PR={tuning.score:.4f}, "
            f"ROC={roc if roc is not None else float('nan'):.4f}, "
            f"PR={pr if pr is not None else float('nan'):.4f}, "
            f"Spearman(fwd5d)={spearman if spearman is not None else float('nan'):+.4f}, "
            f"Q5-Q1={q5 - q1:+.4%}"
        )

    oos = pd.concat(oos_parts, ignore_index=True)
    oos_target = oos["target"].astype(int)
    oos_probability = oos["ml_probability"].to_numpy(dtype=float)
    oos_forward = oos["forward_return_5d"].astype(float)
    oos_spearman = _safe_spearman(pd.Series(oos_probability), oos_forward)
    oos_roc = _safe_roc_auc(oos_target, oos_probability)
    oos_pr = _safe_pr_auc(oos_target, oos_probability)

    quintiles = summarize_score_quintiles(
        pd.DataFrame(
            {
                "target_weight": oos_probability,
                "target": oos_target.to_numpy(),
                "forward_return_5d": oos_forward.to_numpy(),
                "ml_probability": oos_probability,
                "technical_score": oos_probability,
                "signal_score": oos_probability,
            }
        ),
        score_column="ml_probability",
    )
    q1 = float(
        quintiles.loc[quintiles["quintile"] == "Q1", "mean_forward_return_5d"].iloc[0]
    )
    q5 = float(
        quintiles.loc[quintiles["quintile"] == "Q5", "mean_forward_return_5d"].iloc[0]
    )

    print(
        f"  Aggregate: dataset={len(dataset)}, overall target={dataset['target'].mean():.2%}, "
        f"OOS ROC={oos_roc if oos_roc is not None else float('nan'):.4f}, "
        f"OOS PR={oos_pr if oos_pr is not None else float('nan'):.4f}, "
        f"OOS Spearman(fwd5d)={oos_spearman if oos_spearman is not None else float('nan'):+.4f}, "
        f"Q5-Q1={q5 - q1:+.4%}"
    )

    return {
        "symbol": symbol,
        "threshold": threshold,
        "dataset_rows": len(dataset),
        "dataset_target_rate": float(dataset["target"].mean()),
        "oos_rows": len(oos),
        "oos_target_rate": float(oos_target.mean()),
        "oos_roc": oos_roc if oos_roc is not None else float("nan"),
        "oos_pr": oos_pr if oos_pr is not None else float("nan"),
        "oos_spearman_forward_return_5d": (
            oos_spearman if oos_spearman is not None else float("nan")
        ),
        "q1_mean_forward_return_5d": q1,
        "q5_mean_forward_return_5d": q5,
        "q5_minus_q1_forward_return": q5 - q1,
        "mean_inner_pr_auc": float(np.mean([row["inner_pr_auc"] for row in fold_metrics])),
        "folds": 3,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnostic comparison of fund classification target thresholds on real OOS data."
    )
    parser.add_argument("--symbols", default="AFA,AFT")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    parser.add_argument(
        "--thresholds",
        default="0.00,0.01,0.02,0.03,0.05",
        help="comma-separated diagnostic thresholds; production target remains +3%",
    )
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    try:
        thresholds = tuple(
            float(item.strip())
            for item in args.thresholds.split(",")
            if item.strip()
        )
    except ValueError as exc:
        raise SystemExit(f"invalid thresholds: {exc}") from exc

    if not thresholds:
        raise SystemExit("thresholds cannot be empty")
    if any(threshold <= -1.0 for threshold in thresholds):
        raise SystemExit("all thresholds must be greater than -1")
    if not all(thresholds[i] < thresholds[i + 1] for i in range(len(thresholds) - 1)):
        raise SystemExit("thresholds must be strictly increasing")

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )
    if not symbols:
        raise SystemExit("symbols cannot be empty")

    all_results: list[dict[str, float | int | str]] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            raw, source = _load_fund(
                symbol,
                args.days,
                args.min_db_rows,
                args.chunk_delay,
            )
            raw["pricing_date"] = pd.to_datetime(raw["pricing_date"], errors="raise")
            raw = raw.sort_values("pricing_date").reset_index(drop=True)

            print("=" * 96)
            print(f"Fund: {symbol}")
            print(f"Data source: {source}")
            print(
                f"Threshold diagnostic: {', '.join(f'{threshold:.2%}' for threshold in thresholds)}"
            )
            print("-" * 96)

            for threshold in thresholds:
                print(f"Threshold: > {threshold:.2%}")
                try:
                    result = _run_threshold(
                        symbol,
                        raw=raw,
                        threshold=threshold,
                        gap=args.gap,
                    )
                    all_results.append(result)
                except ValueError as exc:
                    print(f"  INCONCLUSIVE: {type(exc).__name__}: {exc}")
        except Exception as exc:
            failures.append((symbol, f"{type(exc).__name__}: {exc}"))
            print(f"FAILED {symbol}: {type(exc).__name__}: {exc}")

    if failures:
        print("=" * 96)
        print("FAILURES")
        for symbol, message in failures:
            print(f"{symbol}: {message}")
        return 1

    if not all_results:
        print("NO VALID THRESHOLD RESULTS")
        return 2

    frame = pd.DataFrame(all_results)
    print("=" * 96)
    print("CROSS-FUND TARGET THRESHOLD DIAGNOSTIC")
    for _, row in frame.iterrows():
        print(
            f"{row['symbol']} threshold={row['threshold']:.2%}: "
            f"target_rate={row['dataset_target_rate']:.2%}, "
            f"OOS ROC={row['oos_roc']:.4f}, "
            f"PR={row['oos_pr']:.4f}, "
            f"Spearman(fwd5d)={row['oos_spearman_forward_return_5d']:+.4f}, "
            f"Q5-Q1={row['q5_minus_q1_forward_return']:+.4%}"
        )

    print("-" * 96)
    for threshold in thresholds:
        subset = frame[np.isclose(frame["threshold"], threshold)]
        if subset.empty:
            continue
        print(
            f"Threshold {threshold:.2%}: "
            f"mean target={subset['dataset_target_rate'].mean():.2%}, "
            f"mean OOS ROC={subset['oos_roc'].mean():.4f}, "
            f"mean OOS PR={subset['oos_pr'].mean():.4f}, "
            f"mean Spearman(fwd5d)={subset['oos_spearman_forward_return_5d'].mean():+.4f}, "
            f"mean Q5-Q1={subset['q5_minus_q1_forward_return'].mean():+.4%}, "
            f"valid funds={len(subset)}/{len(symbols)}"
        )

    assert (frame["folds"] == 3).all()
    assert (frame["oos_rows"] == 120).all()
    assert (frame["dataset_target_rate"] >= 0.0).all()
    assert (frame["dataset_target_rate"] <= 1.0).all()
    print("REAL FUND TARGET THRESHOLD DIAGNOSTIC PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
