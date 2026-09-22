from __future__ import annotations

import argparse
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


def _safe_metrics(
    y_true: np.ndarray, probability: np.ndarray
) -> tuple[float | None, float]:
    if np.unique(y_true).size < 2:
        return None, float("nan")
    return (
        float(roc_auc_score(y_true, probability)),
        float(average_precision_score(y_true, probability)),
    )


def _direction_row(
    name: str,
    y_true: np.ndarray,
    probability: np.ndarray,
    training_target_rate: float,
    oos_target_rate: float,
    status: str = "ok",
) -> dict[str, float | str | None]:
    roc, pr = _safe_metrics(y_true, probability)
    spearman = float(
        pd.Series(probability).corr(pd.Series(y_true), method="spearman")
    )
    inverse = 1.0 - probability
    inverse_roc, inverse_pr = _safe_metrics(y_true, inverse)
    inverse_spearman = float(
        pd.Series(inverse).corr(pd.Series(y_true), method="spearman")
    )
    return {
        "model": name,
        "status": status,
        "training_target_rate": training_target_rate,
        "oos_target_rate": oos_target_rate,
        "direct_roc": roc,
        "direct_pr": pr,
        "direct_spearman": spearman,
        "inverse_roc": inverse_roc,
        "inverse_pr": inverse_pr,
        "inverse_spearman": inverse_spearman,
    }


def _evaluate_threshold(
    dataset: pd.DataFrame,
    *,
    asset_type: str,
    threshold: float,
    gap: int,
) -> list[dict[str, float | str | None]]:
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    columns = list(feature_columns(asset_type))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )
    baseline_config = XGBoostBaselineConfig()

    rows: list[dict[str, object]] = []
    oos_parts: list[pd.DataFrame] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()
        training_rate = float(train["target"].mean())
        oos_rate = float(test["target"].mean())

        if train["target"].nunique() < 2:
            rows.append(
                {
                    "threshold": threshold,
                    "fold": fold_number,
                    "model": "baseline",
                    "status": "one_class_train",
                    "training_target_rate": training_rate,
                    "oos_target_rate": oos_rate,
                }
            )
            rows.append(
                {
                    "threshold": threshold,
                    "fold": fold_number,
                    "model": "tuned",
                    "status": "one_class_train",
                    "training_target_rate": training_rate,
                    "oos_target_rate": oos_rate,
                }
            )
            continue

        y = test["target"].to_numpy(dtype=int)

        baseline = build_model(baseline_config)
        baseline.fit(train[columns], train["target"].astype(int))
        baseline_p = baseline.predict_proba(test[columns])[:, 1]
        baseline_row = _direction_row(
            "baseline",
            y,
            baseline_p,
            training_rate,
            oos_rate,
        )
        baseline_row["threshold"] = threshold
        baseline_row["fold"] = fold_number
        rows.append(baseline_row)

        try:
            tuning = select_best_candidate(
                train,
                asset_type=asset_type,
                tuning_config=tuning_config,
            )
            tuned = build_model(tuning.config)
            tuned.fit(train[columns], train["target"].astype(int))
            tuned_p = tuned.predict_proba(test[columns])[:, 1]
            tuned_row = _direction_row(
                "tuned",
                y,
                tuned_p,
                training_rate,
                oos_rate,
            )
            tuned_row["threshold"] = threshold
            tuned_row["fold"] = fold_number
            tuned_row["inner_pr_auc"] = tuning.score
            tuned_row["max_depth"] = tuning.config.max_depth
            tuned_row["learning_rate"] = tuning.config.learning_rate
            tuned_row["min_child_weight"] = tuning.config.min_child_weight
            rows.append(tuned_row)
        except ValueError as exc:
            rows.append(
                {
                    "threshold": threshold,
                    "fold": fold_number,
                    "model": "tuned",
                    "status": f"tuning_unavailable:{exc}",
                    "training_target_rate": training_rate,
                    "oos_target_rate": oos_rate,
                }
            )

        oos_parts.append(
            pd.DataFrame(
                {
                    "target": y,
                    "baseline_probability": baseline_p,
                    "forward_return_5d": test["forward_return_5d"].to_numpy(float),
                }
            )
        )
        if "tuned_p" in locals():
            oos_parts[-1]["tuned_probability"] = tuned_p
            del tuned_p

    result_rows = [row for row in rows if row.get("status", "ok") == "ok"]
    for model_name in ("baseline", "tuned"):
        parts = []
        for part in oos_parts:
            column = f"{model_name}_probability"
            if column in part:
                parts.append(part[["target", column]])
        if not parts:
            continue
        combined = pd.concat(parts, ignore_index=True)
        y = combined["target"].to_numpy(dtype=int)
        probability = combined[f"{model_name}_probability"].to_numpy(float)
        aggregate = _direction_row(
            f"{model_name}_aggregate",
            y,
            probability,
            float(dataset["target"].mean()),
            float(y.mean()),
        )
        aggregate["threshold"] = threshold
        aggregate["fold"] = "aggregate"
        result_rows.append(aggregate)

    return result_rows


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

    for threshold in TARGET_THRESHOLDS:
        dataset = build_ml_feature_dataset(
            indicators,
            asset_type=asset_type,
            config=MLFeatureConfig(
                horizon=5,
                positive_return_threshold=threshold,
            ),
        )
        if dataset.empty:
            print(f"\nTarget > {threshold:.0%}: DATASET EMPTY")
            continue

        forward = dataset["forward_return_5d"].to_numpy(dtype=float)
        target_rate = float(dataset["target"].mean())
        print(
            f"\nTarget > {threshold:.0%}: "
            f"rows={len(dataset)}, positive={int(dataset['target'].sum())}, "
            f"rate={target_rate:.3f}"
        )
        print(
            f"  forward mean={np.mean(forward):.4f}, "
            f"median={np.median(forward):.4f}, std={np.std(forward):.4f}"
        )

        metrics = _evaluate_threshold(
            dataset,
            asset_type=asset_type,
            threshold=threshold,
            gap=gap,
        )
        for row in metrics:
            if row["fold"] == "aggregate":
                print(
                    f"  {row['model']}: "
                    f"direct ROC={row['direct_roc'] if row['direct_roc'] is not None else float('nan'):.4f}, "
                    f"PR={row['direct_pr']:.4f}, "
                    f"Spearman={row['direct_spearman']:.4f} | "
                    f"inverse ROC={row['inverse_roc'] if row['inverse_roc'] is not None else float('nan'):.4f}, "
                    f"PR={row['inverse_pr']:.4f}, "
                    f"Spearman={row['inverse_spearman']:.4f}"
                )

        fold_results = {}
        for row in metrics:
            fold = row.get("fold")
            if isinstance(fold, int) and row.get("model") == "baseline":
                fold_results[fold] = row
        direct_positive = sum(
            1
            for row in fold_results.values()
            if row.get("status") == "ok" and row.get("direct_spearman", 0.0) > 0
        )
        print(
            f"  Baseline OOS fold direction: "
            f"{direct_positive}/{len(fold_results)} folds have positive direct Spearman"
        )

    print("TARGET THRESHOLD DIRECTION DIAGNOSTIC PASSED")


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
