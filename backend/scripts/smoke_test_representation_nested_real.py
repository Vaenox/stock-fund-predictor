from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sqlalchemy import create_engine, text

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningCandidate, TuningConfig, default_candidate_grid
from app.ml.xgboost_baseline import build_model
from smoke_test_feature_ablation_real import (
    FUND_FEATURE_COLUMNS,
    STOCK_FEATURE_COLUMNS,
    _prepare_variant,
    _stationary_core_columns,
)


REPRESENTATIONS = ("raw_all", "normalized_all", "stationary_core")
REPRESENTATION_INNER_TEST_SIZE = 40
REPRESENTATION_TUNING_TEST_SIZE = 20


@dataclass(frozen=True, slots=True)
class RepresentationScore:
    representation: str
    mean_pr_auc: float
    mean_roc_auc: float
    fold_pr_std: float
    direction_consistency: float
    valid_folds: int


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


def _safe_auc(metric: str, y: np.ndarray, probability: np.ndarray) -> float | None:
    if np.unique(y).size < 2:
        return None
    if metric == "pr":
        return float(average_precision_score(y, probability))
    return float(roc_auc_score(y, probability))


def _select_best_candidate_for_representation(
    frame: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    tuning_config: TuningConfig,
):
    from app.ml.tuning import TuningCandidate, default_candidate_grid

    scored = []
    for candidate in default_candidate_grid():
        folds = build_walk_forward_splits(
            len(frame),
            n_splits=tuning_config.n_inner_splits,
            test_size=tuning_config.inner_test_size,
            gap=tuning_config.gap,
        )
        fold_scores = []
        for inner_fold in folds:
            train = frame.iloc[inner_fold.train_start : inner_fold.train_end]
            validation = frame.iloc[inner_fold.test_start : inner_fold.test_end]
            if train["target"].nunique() < 2 or validation["target"].nunique() < 2:
                continue
            model = build_model(candidate)
            model.fit(train[list(columns)], train["target"].astype(int))
            probability = model.predict_proba(validation[list(columns)])[:, 1]
            score = _safe_auc("pr", validation["target"].astype(int).to_numpy(), probability)
            if score is not None:
                fold_scores.append(score)
        if len(fold_scores) < tuning_config.n_inner_splits:
            continue
        scored.append(TuningCandidate(config=candidate, score=float(np.mean(fold_scores))))

    if not scored:
        raise ValueError(
            "representation tuning has no candidate with two valid inner folds"
        )

    return max(
        scored,
        key=lambda item: (
            item.score,
            -item.config.max_depth,
            -item.config.learning_rate,
            -item.config.min_child_weight,
        ),
    )


def _score_representation(
    prepared: pd.DataFrame,
    *,
    asset_type: str,
    representation: str,
    columns: tuple[str, ...],
    gap: int,
) -> RepresentationScore | None:
    folds = build_walk_forward_splits(
        len(prepared),
        n_splits=2,
        test_size=REPRESENTATION_INNER_TEST_SIZE,
        gap=gap,
    )
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=REPRESENTATION_TUNING_TEST_SIZE,
        gap=gap,
    )

    pr_scores: list[float] = []
    roc_scores: list[float] = []
    directions: list[float] = []

    for fold in folds:
        train = prepared.iloc[fold.train_start : fold.train_end].dropna(
            subset=list(columns)
        )
        validation = prepared.iloc[fold.test_start : fold.test_end].dropna(
            subset=list(columns)
        )

        if train["target"].nunique() < 2 or validation["target"].nunique() < 2:
            continue

        try:
            tuning = _select_best_candidate_for_representation(
                train,
                columns=columns,
                tuning_config=tuning_config,
            )
        except ValueError as exc:
            print(
                f"[representation={representation}] "
                f"representation-fold train={len(train)} validation={len(validation)} "
                f"train_pos={train['target'].mean():.3f} "
                f"validation_pos={validation['target'].mean():.3f} "
                f"skipped: {exc}"
            )
            continue

        model = build_model(tuning.config)
        model.fit(train[list(columns)], train["target"].astype(int))
        probability = model.predict_proba(validation[list(columns)])[:, 1]
        y = validation["target"].astype(int).to_numpy()

        pr = _safe_auc("pr", y, probability)
        roc = _safe_auc("roc", y, probability)
        if pr is None or roc is None:
            continue

        pr_scores.append(pr)
        roc_scores.append(roc)
        directions.append(
            float(pd.Series(probability).corr(pd.Series(y), method="spearman"))
        )

    if not pr_scores:
        return None

    return RepresentationScore(
        representation=representation,
        mean_pr_auc=float(np.mean(pr_scores)),
        mean_roc_auc=float(np.mean(roc_scores)),
        fold_pr_std=float(np.std(pr_scores)),
        direction_consistency=float(
            np.mean([1.0 if value >= 0 else 0.0 for value in directions])
        ),
        valid_folds=len(pr_scores),
    )

def _select_representation(
    scores: list[RepresentationScore],
    *,
    required_valid_folds: int = 2,
) -> RepresentationScore:
    stable = [
        score for score in scores if score.valid_folds >= required_valid_folds
    ]
    if not stable:
        raise ValueError(
            "no representation has the required number of valid inner folds"
        )

    return max(
        stable,
        key=lambda item: (
            item.mean_pr_auc,
            item.mean_roc_auc,
            -item.fold_pr_std,
            item.valid_folds,
            item.representation,
        ),
    )


def _evaluate_outer(
    frame: pd.DataFrame,
    *,
    asset_type: str,
    representation: str,
    outer_fold_number: int,
    gap: int,
) -> dict[str, object]:
    prepared, columns = _prepare_variant(
        frame,
        asset_type=asset_type,
        variant=representation,
    )
    folds = build_walk_forward_splits(
        len(prepared),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    fold = folds[outer_fold_number - 1]
    train = prepared.iloc[fold.train_start : fold.train_end].dropna(
        subset=list(columns)
    )
    test = prepared.iloc[fold.test_start : fold.test_end].dropna(
        subset=list(columns)
    )

    if train["target"].nunique() < 2:
        raise ValueError(
            f"{representation} fold {outer_fold_number} outer training target contains one class"
        )

    tuning = _select_best_candidate_for_representation(
        train,
        columns=tuple(columns),
        tuning_config=TuningConfig(
            n_inner_splits=2,
            inner_test_size=REPRESENTATION_TUNING_TEST_SIZE,
            gap=gap,
        ),
    )
    model = build_model(tuning.config)
    model.fit(train[list(columns)], train["target"].astype(int))
    probability = model.predict_proba(test[list(columns)])[:, 1]
    y = test["target"].astype(int).to_numpy()

    return {
        "fold": outer_fold_number,
        "representation": representation,
        "outer_rows": len(y),
        "positive_rate": float(y.mean()),
        "roc": _safe_auc("roc", y, probability),
        "pr": _safe_auc("pr", y, probability),
        "spearman": float(
            pd.Series(probability).corr(pd.Series(y), method="spearman")
        ),
        "model": (
            f"d={tuning.config.max_depth},"
            f"lr={tuning.config.learning_rate:.2f},"
            f"mcw={tuning.config.min_child_weight:.1f}"
        ),
    }


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
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
            positive_return_threshold=0.03,
        ),
    )

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Dataset rows: {len(dataset)}")
    print("Production target: horizon=5, threshold=+3%")
    print("Representations:", ", ".join(REPRESENTATIONS))

    outer_results: list[dict[str, object]] = []

    for outer_number in range(1, 4):
        scores: list[RepresentationScore] = []

        for representation in REPRESENTATIONS:
            prepared, _ = _prepare_variant(
                dataset,
                asset_type=asset_type,
                variant=representation,
            )
            outer_folds = build_walk_forward_splits(
                len(prepared),
                n_splits=3,
                test_size=40,
                gap=gap,
            )
            outer_fold = outer_folds[outer_number - 1]
            outer_train = prepared.iloc[: outer_fold.train_end].copy()

            if representation in ("raw_all", "normalized_all"):
                columns = (
                    STOCK_FEATURE_COLUMNS
                    if asset_type == "stock"
                    else FUND_FEATURE_COLUMNS
                )
            else:
                columns = _stationary_core_columns(asset_type)

            score = _score_representation(
                outer_train,
                asset_type=asset_type,
                representation=representation,
                columns=tuple(columns),
                gap=gap,
            )
            if score is not None:
                scores.append(score)

        winner = _select_representation(scores)

        print(
            f"Outer fold {outer_number}: selected {winner.representation} | "
            f"inner PR={winner.mean_pr_auc:.4f}, "
            f"ROC={winner.mean_roc_auc:.4f}, "
            f"PR std={winner.fold_pr_std:.4f}, "
            f"direction={winner.direction_consistency:.0%}, "
            f"valid_folds={winner.valid_folds}"
        )

        result = _evaluate_outer(
            dataset,
            asset_type=asset_type,
            representation=winner.representation,
            outer_fold_number=outer_number,
            gap=gap,
        )
        outer_results.append(result)

    print("\nNESTED REPRESENTATION SELECTION RESULTS")
    for result in outer_results:
        print(
            f"fold={result['fold']} representation={result['representation']}: "
            f"outer rows={result['outer_rows']}, "
            f"positive={result['positive_rate']:.3f}, "
            f"ROC={result['roc'] if result['roc'] is not None else float('nan'):.4f}, "
            f"PR={result['pr'] if result['pr'] is not None else float('nan'):.4f}, "
            f"Spearman={result['spearman']:.4f}, "
            f"model={result['model']}"
        )

    selected = [str(result["representation"]) for result in outer_results]
    print("\nSelected representations by outer fold:", ", ".join(selected))
    print(
        "Production representation remains raw_all until broader evidence is reviewed."
    )
    print("NESTED REPRESENTATION SELECTION PASSED")


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
