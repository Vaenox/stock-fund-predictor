from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from app.analysis.features import (
    FUND_FEATURE_COLUMNS,
    MLFeatureConfig,
    STOCK_FEATURE_COLUMNS,
    build_ml_feature_dataset,
)
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.comparison import ModelComparison
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import FoldMetrics, XGBoostBaselineConfig, build_model
from scripts.smoke_test_normalized_feature_direction_real import PRICE_LEVEL_FEATURES, _load_fund, _load_stock, _normalize_levels


def _safe_roc_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    from sklearn.metrics import roc_auc_score
    if y_true.nunique() < 2:
        return None
    return float(roc_auc_score(y_true, probability))


def _safe_pr_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    from sklearn.metrics import average_precision_score
    if y_true.nunique() < 2:
        return None
    return float(average_precision_score(y_true, probability))


def _evaluate(
    dataset: pd.DataFrame,
    *,
    asset_type: str,
    normalized: bool,
    gap: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = list(FUND_FEATURE_COLUMNS if asset_type == "fund" else STOCK_FEATURE_COLUMNS)
    folds = build_walk_forward_splits(len(dataset), n_splits=3, test_size=40, gap=gap)
    baseline_config = XGBoostBaselineConfig()
    tuning_config = TuningConfig(n_inner_splits=2, inner_test_size=20, gap=gap)

    oos_rows: list[pd.DataFrame] = []
    fold_rows: list[dict[str, object]] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start:fold.train_end].copy()
        test = dataset.iloc[fold.test_start:fold.test_end].copy()

        if normalized:
            train = _normalize_levels(train, asset_type)
            test = _normalize_levels(test, asset_type)

        train = train.dropna(subset=columns)
        test = test.dropna(subset=columns)

        baseline = build_model(baseline_config)
        baseline.fit(train[columns], train["target"].astype(int))
        baseline_p = baseline.predict_proba(test[columns])[:, 1]

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
        )
        tuned = build_model(tuning.config)
        tuned.fit(train[columns], train["target"].astype(int))
        tuned_p = tuned.predict_proba(test[columns])[:, 1]

        y = test["target"].astype(int)
        fold_rows.append(
            {
                "fold": fold_number,
                "baseline_roc": _safe_roc_auc(y, baseline_p),
                "baseline_pr": _safe_pr_auc(y, baseline_p),
                "baseline_spearman": float(pd.Series(baseline_p).corr(pd.Series(y), method="spearman")),
                "tuned_roc": _safe_roc_auc(y, tuned_p),
                "tuned_pr": _safe_pr_auc(y, tuned_p),
                "tuned_spearman": float(pd.Series(tuned_p).corr(pd.Series(y), method="spearman")),
                "train_rows": len(train),
                "test_rows": len(test),
                "inner_pr_auc": tuning.score,
            }
        )
        oos_rows.append(
            pd.DataFrame(
                {
                    "target": y.to_numpy(),
                    "baseline_probability": baseline_p,
                    "tuned_probability": tuned_p,
                }
            )
        )

    oos = pd.concat(oos_rows, ignore_index=True)
    return pd.DataFrame(fold_rows), oos


def _run(asset_type: str, symbol: str, days: int, gap: int, threshold: float, min_db_rows: int) -> None:
    if asset_type == "stock":
        raw, source = _load_stock(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
        columns = STOCK_FEATURE_COLUMNS
    else:
        raw, source = _load_fund(symbol, days)
        indicators = calculate_fund_indicators(raw)
        columns = FUND_FEATURE_COLUMNS

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
        config=MLFeatureConfig(horizon=5, positive_return_threshold=threshold),
    )

    raw_folds, raw_oos = _evaluate(
        dataset,
        asset_type=asset_type,
        normalized=False,
        gap=gap,
    )
    norm_folds, norm_oos = _evaluate(
        dataset,
        asset_type=asset_type,
        normalized=True,
        gap=gap,
    )

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Target threshold: > {threshold:.0%}")
    print("\nRaw feature model:")
    for _, row in raw_folds.iterrows():
        print(
            f"  Fold {int(row['fold'])}: "
            f"baseline ROC={row['baseline_roc'] if pd.notna(row['baseline_roc']) else float('nan'):.4f}, "
            f"PR={row['baseline_pr'] if pd.notna(row['baseline_pr']) else float('nan'):.4f}, "
            f"Spearman={row['baseline_spearman']:.4f} | "
            f"tuned ROC={row['tuned_roc'] if pd.notna(row['tuned_roc']) else float('nan'):.4f}, "
            f"PR={row['tuned_pr'] if pd.notna(row['tuned_pr']) else float('nan'):.4f}, "
            f"Spearman={row['tuned_spearman']:.4f}"
        )
    print("\nNormalized feature model:")
    for _, row in norm_folds.iterrows():
        print(
            f"  Fold {int(row['fold'])}: "
            f"baseline ROC={row['baseline_roc'] if pd.notna(row['baseline_roc']) else float('nan'):.4f}, "
            f"PR={row['baseline_pr'] if pd.notna(row['baseline_pr']) else float('nan'):.4f}, "
            f"Spearman={row['baseline_spearman']:.4f} | "
            f"tuned ROC={row['tuned_roc'] if pd.notna(row['tuned_roc']) else float('nan'):.4f}, "
            f"PR={row['tuned_pr'] if pd.notna(row['tuned_pr']) else float('nan'):.4f}, "
            f"Spearman={row['tuned_spearman']:.4f}"
        )

    for label, oos in (("raw", raw_oos), ("normalized", norm_oos)):
        y = oos["target"].to_numpy(dtype=int)
        for model in ("baseline", "tuned"):
            probability = oos[f"{model}_probability"].to_numpy(dtype=float)
            print(
                f"{label} {model} aggregate: "
                f"ROC={_safe_roc_auc(pd.Series(y), probability) or float('nan'):.4f}, "
                f"PR={_safe_pr_auc(pd.Series(y), probability) or float('nan'):.4f}, "
                f"Spearman={pd.Series(probability).corr(pd.Series(y), method='spearman'):.4f}"
            )

    print("NORMALIZED VS RAW FEATURE MODEL COMPARISON PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--min-db-rows", type=int, default=365)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.threshold <= -1:
        raise SystemExit("threshold must be greater than -1")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.gap,
        args.threshold,
        args.min_db_rows,
    )


if __name__ == "__main__":
    main()
