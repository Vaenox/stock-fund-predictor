from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import XGBoostBaselineConfig, build_model


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame(
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
    )


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records: list = []
    chunks = tuple(
        provider._chunks(
            start_date,
            end_date,
            provider._settings.max_days_per_request,
        )
    )
    for index, (chunk_start, chunk_end) in enumerate(chunks):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
        if index < len(chunks) - 1 and chunk_delay > 0:
            time.sleep(chunk_delay)
    return (
        pd.DataFrame(
            {
                "pricing_date": [r.pricing_date for r in records],
                "unit_price": [float(r.unit_price) for r in records],
            }
        )
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )


def _safe_metrics(
    y_true: np.ndarray, probability: np.ndarray
) -> tuple[float | None, float]:
    if np.unique(y_true).size < 2:
        return None, float("nan")
    return (
        float(roc_auc_score(y_true, probability)),
        float(average_precision_score(y_true, probability)),
    )


def _describe(name: str, y: np.ndarray, probability: np.ndarray) -> None:
    roc, pr = _safe_metrics(y, probability)
    spear = float(pd.Series(probability).corr(pd.Series(y), method="spearman"))
    inverse = 1.0 - probability
    inv_roc, inv_pr = _safe_metrics(y, inverse)
    inv_spear = float(pd.Series(inverse).corr(pd.Series(y), method="spearman"))
    print(
        f"  {name}: direct ROC={roc if roc is not None else float('nan'):.4f}, "
        f"PR={pr:.4f}, Spearman={spear:.4f} | "
        f"inverse ROC={inv_roc if inv_roc is not None else float('nan'):.4f}, "
        f"PR={inv_pr:.4f}, Spearman={inv_spear:.4f}"
    )


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
    chunk_delay: float,
) -> None:
    if asset_type == "stock":
        raw = _stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
    else:
        raw = _fund_frame(symbol, days, chunk_delay)
        indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    features = list(feature_columns(asset_type))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )
    baseline_config = XGBoostBaselineConfig()

    rows: list[dict] = []
    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()
        if train["target"].nunique() < 2:
            raise ValueError(f"fold {fold_number} training target contains one class")

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
        )
        baseline = build_model(baseline_config)
        tuned = build_model(tuning.config)

        baseline.fit(train[features], train["target"].astype(int))
        tuned.fit(train[features], train["target"].astype(int))

        baseline_p = baseline.predict_proba(test[features])[:, 1]
        tuned_p = tuned.predict_proba(test[features])[:, 1]
        y = test["target"].to_numpy(dtype=int)

        print(
            f"Fold {fold_number}: tuned depth={tuning.config.max_depth}, "
            f"lr={tuning.config.learning_rate:.2f}, "
            f"mcw={tuning.config.min_child_weight:.1f}, "
            f"inner PR-AUC={tuning.score:.4f}"
        )
        _describe("baseline", y, baseline_p)
        _describe("tuned", y, tuned_p)

        for index in range(len(test)):
            rows.append(
                {
                    "target": int(y[index]),
                    "baseline_probability": float(baseline_p[index]),
                    "tuned_probability": float(tuned_p[index]),
                    "forward_return_5d": float(
                        test.iloc[index]["forward_return_5d"]
                    ),
                }
            )

    oos = pd.DataFrame(rows)
    y = oos["target"].to_numpy(dtype=int)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Target rate: {y.mean():.3f}")
    _describe(
        "baseline aggregate",
        y,
        oos["baseline_probability"].to_numpy(dtype=float),
    )
    _describe(
        "tuned aggregate",
        y,
        oos["tuned_probability"].to_numpy(dtype=float),
    )

    assert len(oos) > 0
    print("MODEL DIRECTION COMPARISON PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    _run(args.asset_type, args.symbol, args.days, args.gap, args.chunk_delay)


if __name__ == "__main__":
    main()
