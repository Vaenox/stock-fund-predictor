from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import (
    FUND_FEATURE_COLUMNS,
    MLFeatureConfig,
    STOCK_FEATURE_COLUMNS,
    build_ml_feature_dataset,
)
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.splitting import build_inner_splits, build_walk_forward_splits
from app.ml.tuning import TuningCandidate, TuningConfig, default_candidate_grid
from app.ml.xgboost_baseline import XGBoostBaselineConfig, build_model


PRICE_RATIO_FEATURES = {
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_20",
    "ema_50",
    "ema_200",
    "bb_mid",
    "bb_upper",
    "bb_lower",
}
PRICE_PER_PRICE_FEATURES = {
    "atr_14",
    "macd",
    "macd_signal",
    "macd_hist",
}

STATIONARY_CORE_STOCK = (
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_width",
    "bb_position",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "return_1d",
    "return_5d",
    "volatility_20",
    "atr_pct_14",
    "adx_14",
    "volume_ratio_20",
    "volume_change_1d",
)

STATIONARY_CORE_FUND = (
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_width",
    "bb_position",
    "momentum_5",
    "momentum_10",
    "momentum_20",
    "return_1d",
    "return_5d",
    "volatility_20",
)


def _load_stock(symbol: str, days: int, min_db_rows: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT b.trading_date, b.open, b.high, b.low, b.close, b.volume
                FROM stock_daily_bars b
                JOIN assets a ON a.id = b.asset_id
                WHERE a.canonical_symbol = :symbol
                  AND b.trading_date BETWEEN :start_date AND :end_date
                ORDER BY b.trading_date
                """
            ),
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

    if len(rows) >= min_db_rows:
        return pd.DataFrame(rows), "PostgreSQL canonical history"

    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    if not records:
        raise ValueError(f"no Borsapy history found for {symbol}")

    return (
        pd.DataFrame(
            {
                "trading_date": [r.trading_date for r in records],
                "open": [float(r.open) for r in records],
                "high": [float(r.high) for r in records],
                "low": [float(r.low) for r in records],
                "close": [float(r.close) for r in records],
                "volume": [
                    float(r.volume) if r.volume is not None else float("nan")
                    for r in records
                ],
            }
        ),
        "Borsapy provider (DB history insufficient)",
    )


def _load_fund(symbol: str, days: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT p.pricing_date, p.unit_price
                FROM fund_daily_prices p
                JOIN assets a ON a.id = p.asset_id
                WHERE a.canonical_symbol = :symbol
                  AND p.pricing_date BETWEEN :start_date AND :end_date
                ORDER BY p.pricing_date
                """
            ),
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

    if not rows:
        raise ValueError(f"no DB fund history found for {symbol}")

    return pd.DataFrame(rows), "PostgreSQL canonical history"


def _normalize_levels(dataset: pd.DataFrame, asset_type: str) -> pd.DataFrame:
    result = dataset.copy()
    price = result["close"] if asset_type == "stock" else result["unit_price"]
    price_safe = pd.to_numeric(price, errors="coerce").replace(0, np.nan)

    for column in PRICE_RATIO_FEATURES:
        if column in result.columns:
            result[column] = result[column] / price_safe - 1.0

    for column in PRICE_PER_PRICE_FEATURES:
        if column in result.columns:
            result[column] = result[column] / price_safe

    if "volume_sma_20" in result.columns and "volume" in result.columns:
        volume = pd.to_numeric(result["volume"], errors="coerce").replace(0, np.nan)
        result["volume_sma_20"] = result["volume_sma_20"] / volume - 1.0

    return result.replace([np.inf, -np.inf], np.nan)


def _stationary_core_columns(asset_type: str) -> tuple[str, ...]:
    return (
        STATIONARY_CORE_STOCK
        if asset_type == "stock"
        else STATIONARY_CORE_FUND
    )


def _prepare_variant(
    dataset: pd.DataFrame,
    *,
    asset_type: str,
    variant: str,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    if variant == "raw_all":
        return dataset.copy(), tuple(
            STOCK_FEATURE_COLUMNS if asset_type == "stock" else FUND_FEATURE_COLUMNS
        )

    normalized = _normalize_levels(dataset, asset_type)
    if variant == "normalized_all":
        return normalized, tuple(
            STOCK_FEATURE_COLUMNS if asset_type == "stock" else FUND_FEATURE_COLUMNS
        )

    if variant == "stationary_core":
        return normalized, _stationary_core_columns(asset_type)

    raise ValueError(f"unsupported variant: {variant}")


def _safe_roc_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(roc_auc_score(y_true, probability))


def _safe_pr_auc(y_true: pd.Series, probability: np.ndarray) -> float | None:
    if y_true.nunique() < 2:
        return None
    return float(average_precision_score(y_true, probability))


def _score_candidate_inner(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    candidate: XGBoostBaselineConfig,
    tuning_config: TuningConfig,
) -> float:
    folds = build_inner_splits(len(frame), config=tuning_config)
    fold_scores: list[float] = []

    for fold in folds:
        train = frame.iloc[fold.train_start : fold.train_end]
        validation = frame.iloc[fold.test_start : fold.test_end]

        if train["target"].nunique() < 2:
            raise ValueError("inner training target contains only one class")

        model = build_model(candidate)
        model.fit(train[list(columns)], train["target"].astype(int))
        probability = model.predict_proba(validation[list(columns)])[:, 1]

        score = _safe_pr_auc(validation["target"], probability)
        if score is not None:
            fold_scores.append(score)

    if not fold_scores:
        raise ValueError("inner validation has no two-class fold")

    return float(sum(fold_scores) / len(fold_scores))


def _select_best_candidate(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    tuning_config: TuningConfig,
) -> TuningCandidate:
    scored: list[TuningCandidate] = []

    for candidate in default_candidate_grid():
        score = _score_candidate_inner(
            frame,
            columns=columns,
            candidate=candidate,
            tuning_config=tuning_config,
        )
        scored.append(TuningCandidate(config=candidate, score=score))

    return max(
        scored,
        key=lambda item: (
            item.score,
            -item.config.max_depth,
            -item.config.learning_rate,
            -item.config.min_child_weight,
        ),
    )


def _evaluate_variant(
    dataset: pd.DataFrame,
    *,
    asset_type: str,
    variant: str,
    gap: int,
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[str, ...]]:
    prepared, columns = _prepare_variant(
        dataset,
        asset_type=asset_type,
        variant=variant,
    )

    folds = build_walk_forward_splits(
        len(prepared),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    baseline_config = XGBoostBaselineConfig()
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )

    fold_rows: list[dict[str, object]] = []
    oos_parts: list[pd.DataFrame] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = prepared.iloc[fold.train_start : fold.train_end].copy()
        test = prepared.iloc[fold.test_start : fold.test_end].copy()

        train = train.dropna(subset=list(columns))
        test = test.dropna(subset=list(columns))

        if train["target"].nunique() < 2:
            raise ValueError(
                f"{variant} fold {fold_number} training target contains only one class"
            )

        baseline = build_model(baseline_config)
        baseline.fit(train[list(columns)], train["target"].astype(int))
        baseline_probability = baseline.predict_proba(test[list(columns)])[:, 1]

        tuning = _select_best_candidate(
            train,
            columns=columns,
            tuning_config=tuning_config,
        )
        tuned = build_model(tuning.config)
        tuned.fit(train[list(columns)], train["target"].astype(int))
        tuned_probability = tuned.predict_proba(test[list(columns)])[:, 1]

        target = test["target"].astype(int).reset_index(drop=True)
        baseline_series = pd.Series(baseline_probability)
        tuned_series = pd.Series(tuned_probability)

        fold_rows.append(
            {
                "fold": fold_number,
                "baseline_roc": _safe_roc_auc(target, baseline_probability),
                "baseline_pr": _safe_pr_auc(target, baseline_probability),
                "baseline_spearman": baseline_series.corr(
                    target,
                    method="spearman",
                ),
                "tuned_roc": _safe_roc_auc(target, tuned_probability),
                "tuned_pr": _safe_pr_auc(target, tuned_probability),
                "tuned_spearman": tuned_series.corr(
                    target,
                    method="spearman",
                ),
                "train_rows": len(train),
                "test_rows": len(test),
                "inner_pr_auc": tuning.score,
            }
        )

        oos_parts.append(
            pd.DataFrame(
                {
                    "target": target.to_numpy(),
                    "baseline_probability": baseline_probability,
                    "tuned_probability": tuned_probability,
                }
            )
        )

    return pd.DataFrame(fold_rows), pd.concat(oos_parts, ignore_index=True), columns


def _print_fold_results(
    fold_rows: pd.DataFrame,
    *,
    variant: str,
) -> None:
    print(f"\n{variant}:")
    for _, row in fold_rows.iterrows():
        print(
            f"  Fold {int(row['fold'])}: "
            f"baseline ROC={row['baseline_roc'] if pd.notna(row['baseline_roc']) else float('nan'):.4f}, "
            f"PR={row['baseline_pr'] if pd.notna(row['baseline_pr']) else float('nan'):.4f}, "
            f"Spearman={row['baseline_spearman'] if pd.notna(row['baseline_spearman']) else float('nan'):.4f} | "
            f"tuned ROC={row['tuned_roc'] if pd.notna(row['tuned_roc']) else float('nan'):.4f}, "
            f"PR={row['tuned_pr'] if pd.notna(row['tuned_pr']) else float('nan'):.4f}, "
            f"Spearman={row['tuned_spearman'] if pd.notna(row['tuned_spearman']) else float('nan'):.4f}"
        )


def _print_aggregate(
    variant: str,
    oos: pd.DataFrame,
) -> dict[str, float]:
    y = oos["target"].astype(int)

    metrics: dict[str, float] = {}
    for model in ("baseline", "tuned"):
        probability = oos[f"{model}_probability"].to_numpy(dtype=float)
        roc = _safe_roc_auc(y, probability)
        pr = _safe_pr_auc(y, probability)
        spearman = pd.Series(probability).corr(y.reset_index(drop=True), method="spearman")
        metrics[f"{model}_roc"] = roc if roc is not None else float("nan")
        metrics[f"{model}_pr"] = pr if pr is not None else float("nan")
        metrics[f"{model}_spearman"] = (
            float(spearman) if pd.notna(spearman) else float("nan")
        )
        print(
            f"{variant} {model} aggregate: "
            f"ROC={metrics[f'{model}_roc']:.4f}, "
            f"PR={metrics[f'{model}_pr']:.4f}, "
            f"Spearman={metrics[f'{model}_spearman']:.4f}"
        )

    return metrics


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
    threshold: float,
    min_db_rows: int,
) -> None:
    if asset_type == "stock":
        raw, source = _load_stock(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
    else:
        raw, source = _load_fund(symbol, days)
        indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
        config=MLFeatureConfig(
            horizon=5,
            positive_return_threshold=threshold,
        ),
    )

    variants = ("raw_all", "normalized_all", "stationary_core")
    results: dict[str, dict[str, float]] = {}

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Dataset rows: {len(dataset)}")
    print(f"Target threshold: > {threshold:.0%}")

    for variant in variants:
        fold_rows, oos, columns = _evaluate_variant(
            dataset,
            asset_type=asset_type,
            variant=variant,
            gap=gap,
        )
        _print_fold_results(fold_rows, variant=variant)
        print(f"  Feature count: {len(columns)}")
        print(f"  Features: {', '.join(columns)}")
        results[variant] = _print_aggregate(variant, oos)

    print("\nAblation summary (tuned aggregate):")
    for variant in variants:
        metrics = results[variant]
        print(
            f"  {variant}: "
            f"ROC={metrics['tuned_roc']:.4f}, "
            f"PR={metrics['tuned_pr']:.4f}, "
            f"Spearman={metrics['tuned_spearman']:.4f}"
        )

    best_by_pr = max(
        variants,
        key=lambda item: (
            results[item]["tuned_pr"],
            results[item]["tuned_roc"],
            results[item]["tuned_spearman"],
        ),
    )
    print(f"Observed highest tuned PR-AUC in this run: {best_by_pr}")
    print("FEATURE ABLATION REAL SMOKE TEST PASSED")


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
