from __future__ import annotations

import argparse
from datetime import date

import numpy as np
import pandas as pd

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators
from app.ml.feature_importance import calculate_gain_importance
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_backtest_fund_real import _load_fund, _select_best_candidate_sparse


def _safe_spearman(left: pd.Series, right: pd.Series) -> float:
    clean = pd.concat([left, right], axis=1).dropna()
    if len(clean) < 3 or clean.iloc[:, 0].nunique() < 2 or clean.iloc[:, 1].nunique() < 2:
        return float("nan")
    value = clean.iloc[:, 0].corr(clean.iloc[:, 1], method="spearman")
    return float(value) if pd.notna(value) else float("nan")


def _fold_feature_report(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    asset_type: str,
    feature_names: tuple[str, ...],
    tuning_config: TuningConfig,
) -> tuple[pd.DataFrame, float]:
    tuning = _select_best_candidate_sparse(
        train,
        asset_type=asset_type,
        tuning_config=tuning_config,
    )
    model = fit_baseline_model(
        train,
        asset_type=asset_type,
        config=tuning.config,
    )

    importance = {
        row.feature: row.importance
        for row in calculate_gain_importance(model, asset_type=asset_type)
    }
    total_gain = sum(importance.values())
    rows: list[dict[str, object]] = []

    for feature in feature_names:
        forward_spearman = _safe_spearman(
            test[feature],
            test["forward_return_5d"],
        )
        target_spearman = _safe_spearman(
            test[feature],
            test["target"].astype(float),
        )
        raw_gain = float(importance.get(feature, 0.0))
        normalized_gain = raw_gain / total_gain if total_gain > 0 else 0.0
        rows.append(
            {
                "feature": feature,
                "forward_spearman": forward_spearman,
                "target_spearman": target_spearman,
                "gain": raw_gain,
                "normalized_gain": normalized_gain,
            }
        )

    return pd.DataFrame(rows), float(tuning.score)


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    min_db_rows: int,
    threshold: float,
    chunk_delay: float,
) -> None:
    raw, source = _load_fund(symbol, days, min_db_rows, chunk_delay)
    raw["pricing_date"] = pd.to_datetime(raw["pricing_date"], errors="raise")
    raw = raw.sort_values("pricing_date").reset_index(drop=True)
    indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type="fund",
        config=None,
    )
    dataset["target"] = (
        dataset["forward_return_5d"] > threshold
    ).astype("int64")

    if len(dataset) <= 3 * 40 + gap:
        raise ValueError(
            f"not enough dataset observations for 3x40 outer OOS: {len(dataset)}"
        )

    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    feature_names = tuple(feature_columns("fund"))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )

    fold_reports: list[pd.DataFrame] = []

    print("=" * 112)
    print(f"Fund: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(
        f"Regime stability diagnostic: target=h5/{threshold:.2%} | "
        f"OOS=3x40 | gap={gap}"
    )
    print("-" * 112)

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        report, inner_pr = _fold_feature_report(
            train,
            test,
            asset_type="fund",
            feature_names=feature_names,
            tuning_config=tuning_config,
        )
        report["fold"] = fold_number
        fold_reports.append(report)

        top_gain = report.sort_values(
            ["normalized_gain", "feature"],
            ascending=[False, True],
        ).head(8)
        top_forward = report.assign(
            abs_forward_spearman=report["forward_spearman"].abs()
        ).sort_values(
            ["abs_forward_spearman", "feature"],
            ascending=[False, True],
        ).head(8)

        print(
            f"Fold {fold_number}: train target={train['target'].mean():.2%}, "
            f"OOS target={test['target'].mean():.2%}, inner PR={inner_pr:.4f}, "
            f"window={test['pricing_date'].min().date()} -> {test['pricing_date'].max().date()}"
        )
        print("  Top gain features:")
        for row in top_gain.itertuples(index=False):
            print(
                f"    {row.feature}: norm_gain={row.normalized_gain:.4f}, "
                f"fwd_spearman={row.forward_spearman:+.4f}"
            )
        print("  Strongest feature -> forward-return relationships:")
        for row in top_forward.itertuples(index=False):
            print(
                f"    {row.feature}: fwd_spearman={row.forward_spearman:+.4f}, "
                f"norm_gain={row.normalized_gain:.4f}"
            )

    all_folds = pd.concat(fold_reports, ignore_index=True)
    summary_rows: list[dict[str, object]] = []

    for feature in feature_names:
        subset = all_folds[all_folds["feature"] == feature].copy()
        forward = subset["forward_spearman"].to_numpy(dtype=float)
        target = subset["target_spearman"].to_numpy(dtype=float)
        gains = subset["normalized_gain"].to_numpy(dtype=float)

        valid_forward = forward[np.isfinite(forward)]
        valid_target = target[np.isfinite(target)]

        forward_signs = np.sign(valid_forward)
        target_signs = np.sign(valid_target)
        positive_forward_folds = int((valid_forward > 0).sum())
        negative_forward_folds = int((valid_forward < 0).sum())
        positive_target_folds = int((valid_target > 0).sum())
        negative_target_folds = int((valid_target < 0).sum())

        summary_rows.append(
            {
                "feature": feature,
                "mean_forward_spearman": (
                    float(np.mean(valid_forward)) if len(valid_forward) else float("nan")
                ),
                "forward_spearman_std": (
                    float(np.std(valid_forward, ddof=0))
                    if len(valid_forward)
                    else float("nan")
                ),
                "forward_positive_folds": positive_forward_folds,
                "forward_negative_folds": negative_forward_folds,
                "forward_sign_consistency": (
                    float(abs(forward_signs.sum()) / len(forward_signs))
                    if len(forward_signs)
                    else float("nan")
                ),
                "mean_target_spearman": (
                    float(np.mean(valid_target)) if len(valid_target) else float("nan")
                ),
                "target_positive_folds": positive_target_folds,
                "target_negative_folds": negative_target_folds,
                "mean_normalized_gain": float(np.mean(gains)),
                "gain_std": float(np.std(gains, ddof=0)),
                "gain_top3_folds": int((subset["normalized_gain"].rank(ascending=False, method="min") <= 3).sum()),
            }
        )

    summary = pd.DataFrame(summary_rows)
    unstable = summary.sort_values(
        ["forward_spearman_std", "feature"],
        ascending=[False, True],
    ).head(8)
    stable_top = summary.assign(
        abs_mean_forward=summary["mean_forward_spearman"].abs()
    ).sort_values(
        ["abs_mean_forward", "mean_normalized_gain", "feature"],
        ascending=[False, False, True],
    ).head(10)

    print("-" * 112)
    print("Feature forward-return stability:")
    for row in stable_top.itertuples(index=False):
        print(
            f"  {row.feature}: mean_fwd={row.mean_forward_spearman:+.4f}, "
            f"std={row.forward_spearman_std:.4f}, "
            f"signs=+{row.forward_positive_folds}/-{row.forward_negative_folds}, "
            f"gain={row.mean_normalized_gain:.4f}"
        )

    print("Most unstable feature directions:")
    for row in unstable.itertuples(index=False):
        print(
            f"  {row.feature}: mean_fwd={row.mean_forward_spearman:+.4f}, "
            f"std={row.forward_spearman_std:.4f}, "
            f"signs=+{row.forward_positive_folds}/-{row.forward_negative_folds}"
        )

    gain_top = summary.assign(
        abs_mean_forward=summary["mean_forward_spearman"].abs()
    ).sort_values(
        ["mean_normalized_gain", "feature"],
        ascending=[False, True],
    ).head(10)
    print("Top mean normalized-gain features:")
    for row in gain_top.itertuples(index=False):
        print(
            f"  {row.feature}: mean_gain={row.mean_normalized_gain:.4f}, "
            f"gain_std={row.gain_std:.4f}, top3_folds={row.gain_top3_folds}/3, "
            f"mean_fwd={row.mean_forward_spearman:+.4f}"
        )

    all_folds["abs_forward_spearman"] = all_folds["forward_spearman"].abs()
    overall_direction = all_folds["forward_spearman"].dropna()
    print("-" * 112)
    print(
        f"Aggregate fold-feature observations: {len(all_folds)} | "
        f"positive forward directions={int((overall_direction > 0).sum())} | "
        f"negative={int((overall_direction < 0).sum())}"
    )
    print("REAL FUND FEATURE REGIME STABILITY DIAGNOSTIC PASSED")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure fund feature direction and XGBoost gain stability across outer OOS folds."
    )
    parser.add_argument("--symbols", default="AFA,AFT")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")
    if args.threshold <= -1.0:
        raise SystemExit("threshold must be greater than -1")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )
    if not symbols:
        raise SystemExit("symbols cannot be empty")

    failures: list[tuple[str, str]] = []
    for symbol in symbols:
        try:
            _run_symbol(
                symbol,
                days=args.days,
                gap=args.gap,
                min_db_rows=args.min_db_rows,
                threshold=args.threshold,
                chunk_delay=args.chunk_delay,
            )
        except Exception as exc:
            failures.append((symbol, f"{type(exc).__name__}: {exc}"))
            print(f"FAILED {symbol}: {type(exc).__name__}: {exc}")

    if failures:
        print("=" * 112)
        print("FAILURES")
        for symbol, message in failures:
            print(f"{symbol}: {message}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
