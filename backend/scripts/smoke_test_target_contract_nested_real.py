from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import XGBoostBaselineConfig, build_model


TARGET_THRESHOLDS = (0.01, 0.02, 0.03, 0.05)
TARGET_HORIZONS = (3, 5, 10)


@dataclass(frozen=True, slots=True)
class TargetCandidate:
    horizon: int
    threshold: float


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate: TargetCandidate
    mean_pr_auc: float
    mean_roc_auc: float
    fold_pr_std: float
    positive_rate: float
    direction_consistency: float
    valid_folds: int


def _load_stock(symbol: str, days: int, min_db_rows: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
    query = text(
        """
        SELECT b.trading_date, b.open, b.high, b.low, b.close, b.volume
        FROM stock_daily_bars b
        JOIN assets a ON a.id = b.asset_id
        WHERE a.canonical_symbol = :symbol
          AND b.trading_date BETWEEN :start_date AND :end_date
        ORDER BY b.trading_date
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            query,
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
                "trading_date": [record.trading_date for record in records],
                "open": [float(record.open) for record in records],
                "high": [float(record.high) for record in records],
                "low": [float(record.low) for record in records],
                "close": [float(record.close) for record in records],
                "volume": [
                    float(record.volume) if record.volume is not None else float("nan")
                    for record in records
                ],
            }
        ),
        "Borsapy provider (DB history insufficient)",
    )


def _load_fund(symbol: str, days: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
    query = text(
        """
        SELECT p.pricing_date, p.unit_price
        FROM fund_daily_prices p
        JOIN assets a ON a.id = p.asset_id
        WHERE a.canonical_symbol = :symbol
          AND p.pricing_date BETWEEN :start_date AND :end_date
        ORDER BY p.pricing_date
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

    if not rows:
        raise ValueError(f"no DB fund history found for {symbol}")
    return pd.DataFrame(rows), "PostgreSQL canonical history"


def _safe_metric(metric: str, y: np.ndarray, probability: np.ndarray) -> float | None:
    if np.unique(y).size < 2:
        return None
    if metric == "pr":
        return float(average_precision_score(y, probability))
    return float(roc_auc_score(y, probability))


def _candidate_score(
    candidate: TargetCandidate,
    outer_train: pd.DataFrame,
    *,
    asset_type: str,
    outer_gap: int,
) -> CandidateScore | None:
    # Target selection is itself nested: each target candidate gets its own
    # inner hyperparameter tuning, and only that candidate's tuned model is
    # scored on the inner validation folds.
    split_gap = max(outer_gap, candidate.horizon)
    folds = build_walk_forward_splits(
        len(outer_train),
        n_splits=2,
        test_size=20,
        gap=split_gap,
    )
    columns = list(feature_columns(asset_type))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=split_gap,
    )
    pr_scores: list[float] = []
    roc_scores: list[float] = []
    direct_directions: list[float] = []
    fold_rates: list[float] = []

    for fold in folds:
        train = outer_train.iloc[fold.train_start : fold.train_end]
        validation = outer_train.iloc[fold.test_start : fold.test_end]
        if train["target"].nunique() < 2 or validation["target"].nunique() < 2:
            continue

        try:
            tuning = select_best_candidate(
                train,
                asset_type=asset_type,
                tuning_config=tuning_config,
            )
        except ValueError:
            continue

        model = build_model(tuning.config)
        model.fit(train[columns], train["target"].astype(int))
        probability = model.predict_proba(validation[columns])[:, 1]
        y = validation["target"].to_numpy(dtype=int)

        pr = _safe_metric("pr", y, probability)
        roc = _safe_metric("roc", y, probability)
        if pr is None or roc is None:
            continue

        pr_scores.append(pr)
        roc_scores.append(roc)
        fold_rates.append(float(y.mean()))
        direct_directions.append(
            float(pd.Series(probability).corr(pd.Series(y), method="spearman"))
        )

    if not pr_scores:
        return None

    return CandidateScore(
        candidate=candidate,
        mean_pr_auc=float(np.mean(pr_scores)),
        mean_roc_auc=float(np.mean(roc_scores)),
        fold_pr_std=float(np.std(pr_scores)),
        positive_rate=float(np.mean(fold_rates)),
        direction_consistency=float(
            np.mean([1.0 if value >= 0 else 0.0 for value in direct_directions])
        ),
        valid_folds=len(pr_scores),
    )

def _select_candidate(
    candidates: list[CandidateScore],
) -> CandidateScore:
    if not candidates:
        raise ValueError("no target candidate has valid inner folds")

    # PR-AUC is the primary objective. The remaining terms are deterministic
    # tie-breakers/diagnostics, not an attempt to optimize a trading outcome.
    return max(
        candidates,
        key=lambda item: (
            item.mean_pr_auc,
            item.mean_roc_auc,
            -item.fold_pr_std,
            -abs(item.positive_rate - 0.20),
            item.valid_folds,
            -item.candidate.horizon,
            -item.candidate.threshold,
        ),
    )


def _evaluate_outer_fold(
    dataset: pd.DataFrame,
    *,
    candidate: TargetCandidate,
    asset_type: str,
    gap: int,
    outer_fold_number: int,
) -> dict[str, float | int | str | None]:
    split_gap = max(gap, candidate.horizon)
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=split_gap,
    )
    fold = folds[outer_fold_number - 1]
    columns = list(feature_columns(asset_type))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=split_gap,
    )

    train = dataset.iloc[fold.train_start : fold.train_end].copy()
    test = dataset.iloc[fold.test_start : fold.test_end].copy()
    if train["target"].nunique() < 2:
        raise ValueError(
            f"selected candidate has one-class outer training target in fold {outer_fold_number}"
        )

    tuning = select_best_candidate(
        train,
        asset_type=asset_type,
        tuning_config=tuning_config,
    )
    model = build_model(tuning.config)
    model.fit(train[columns], train["target"].astype(int))
    probability = model.predict_proba(test[columns])[:, 1]
    y = test["target"].astype(int).to_numpy()

    return {
        "candidate": f"h={candidate.horizon},t={candidate.threshold:.0%}",
        "outer_rows": int(len(y)),
        "outer_positive_rate": float(y.mean()),
        "outer_roc_auc": _safe_metric("roc", y, probability),
        "outer_pr_auc": _safe_metric("pr", y, probability),
        "outer_direct_spearman": float(
            pd.Series(probability).corr(pd.Series(y), method="spearman")
        ),
        "selected_model_config": (
            f"d={tuning.config.max_depth},lr={tuning.config.learning_rate:.2f},"
            f"mcw={tuning.config.min_child_weight:.1f}"
        ),
    }

def _run(asset_type: str, symbol: str, days: int, gap: int, min_db_rows: int) -> None:
    if asset_type == "stock":
        raw, source = _load_stock(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
    else:
        raw, source = _load_fund(symbol, days)
        indicators = calculate_fund_indicators(raw)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")

    candidates = [
        TargetCandidate(horizon=horizon, threshold=threshold)
        for horizon in TARGET_HORIZONS
        for threshold in TARGET_THRESHOLDS
    ]

    for outer_number, outer_candidate in enumerate(candidates, start=1):
        print(f"Candidate {outer_number}/{len(candidates)}: h={outer_candidate.horizon}, threshold={outer_candidate.threshold:.0%}")

    candidate_results: dict[TargetCandidate, pd.DataFrame] = {}
    for candidate in candidates:
        dataset = build_ml_feature_dataset(
            indicators,
            asset_type=asset_type,
            config=MLFeatureConfig(
                horizon=candidate.horizon,
                positive_return_threshold=candidate.threshold,
            ),
        )
        candidate_results[candidate] = dataset

    common_outer_results: list[dict] = []
    for outer_number in range(1, 4):
        selected: list[CandidateScore] = []
        for candidate in candidates:
            dataset = candidate_results[candidate]
            # Use the same chronological outer fraction for each candidate.
            # Different horizons naturally shorten only the dataset tail.
            folds = build_walk_forward_splits(
                len(dataset),
                n_splits=3,
                test_size=40,
                gap=max(gap, candidate.horizon),
            )
            outer_fold = folds[outer_number - 1]
            outer_train = dataset.iloc[: outer_fold.train_end].copy()
            score = _candidate_score(
                candidate,
                outer_train,
                asset_type=asset_type,
                outer_gap=gap,
            )
            if score is not None:
                selected.append(score)

        winner = _select_candidate(selected)
        print(
            f"Outer fold {outer_number}: selected h={winner.candidate.horizon}, "
            f"threshold={winner.candidate.threshold:.0%} | "
            f"inner PR={winner.mean_pr_auc:.4f}, ROC={winner.mean_roc_auc:.4f}, "
            f"PR std={winner.fold_pr_std:.4f}, "
            f"positive={winner.positive_rate:.3f}, "
            f"direction={winner.direction_consistency:.0%}, "
            f"valid_folds={winner.valid_folds}"
        )

        final_dataset = candidate_results[winner.candidate]
        outer_eval = _evaluate_outer_fold(
            final_dataset,
            candidate=winner.candidate,
            asset_type=asset_type,
            gap=gap,
            outer_fold_number=outer_number,
        )
        outer_eval["selected_outer_fold"] = outer_number
        common_outer_results.append(outer_eval)

    print("\nNESTED TARGET-CONTRACT SELECTION RESULTS")
    for result in common_outer_results:
        print(
            f"  fold={result['selected_outer_fold']} "
            f"{result['candidate']}: "
            f"outer rows={result['outer_rows']}, "
            f"positive={result['outer_positive_rate']:.3f}, "
            f"ROC={result['outer_roc_auc'] if result['outer_roc_auc'] is not None else float('nan'):.4f}, "
            f"PR={result['outer_pr_auc'] if result['outer_pr_auc'] is not None else float('nan'):.4f}, "
            f"Spearman={result['outer_direct_spearman']:.4f}, "
            f"model={result['selected_model_config']}"
        )

    print("\nProduction contract remains horizon=5, threshold=+3% until broader evidence is reviewed.")
    print("NESTED TARGET-CONTRACT SELECTION PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.gap,
        args.min_db_rows,
    )


if __name__ == "__main__":
    main()
