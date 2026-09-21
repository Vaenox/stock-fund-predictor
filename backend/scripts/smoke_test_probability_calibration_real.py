from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.probability_calibration import (
    apply_probability_calibrator,
    evaluate_probability_calibration,
    fit_probability_calibrator,
)
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import fit_baseline_model


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
        provider._chunks(start_date, end_date, provider._settings.max_days_per_request)
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


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
    calibration_size: int,
    chunk_delay: float,
) -> None:
    if asset_type == "stock":
        raw = _stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
        scored = calculate_stock_technical_score(indicators)
        date_column = "trading_date"
        risk_fn = calculate_stock_risk_adjustment
    else:
        raw = _fund_frame(symbol, days, chunk_delay)
        indicators = calculate_fund_indicators(raw)
        scored = calculate_fund_technical_score(indicators)
        date_column = "pricing_date"
        risk_fn = calculate_fund_risk_adjustment

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    feature_list = list(feature_columns(asset_type))
    scored_lookup = scored.set_index(date_column)

    fold_metrics: list[dict[str, object]] = []

    for fold_number, fold in enumerate(folds, start=1):
        outer_train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        calibration_end = len(outer_train)
        calibration_start = calibration_end - calibration_size
        model_train_end = calibration_start - gap

        if model_train_end <= 0:
            raise SystemExit(
                f"fold {fold_number}: not enough training rows for calibration_size={calibration_size}"
            )

        model_train = outer_train.iloc[:model_train_end].copy()
        calibration = outer_train.iloc[calibration_start:calibration_end].copy()

        if calibration["target"].nunique() < 2:
            raise SystemExit(
                f"fold {fold_number}: calibration target contains only one class"
            )
        if model_train["target"].nunique() < 2:
            raise SystemExit(
                f"fold {fold_number}: model training target contains only one class"
            )

        tuning = select_best_candidate(
            model_train,
            asset_type=asset_type,
            tuning_config=TuningConfig(
                n_inner_splits=2,
                inner_test_size=20,
                gap=gap,
            ),
        )
        model = fit_baseline_model(
            model_train,
            asset_type=asset_type,
            config=tuning.config,
        )

        calibration_probability = model.predict_proba(calibration[feature_list])[:, 1]
        outer_probability = model.predict_proba(test[feature_list])[:, 1]

        calibrated: dict[str, np.ndarray] = {"raw": outer_probability}
        for method in ("sigmoid", "isotonic"):
            calibrator = fit_probability_calibrator(
                method,
                calibration_probability,
                calibration["target"].to_numpy(dtype=int),
            )
            calibrated[method] = apply_probability_calibrator(
                calibrator,
                outer_probability,
            )

        y_test = test["target"].to_numpy(dtype=int)

        print(
            f"Fold {fold_number}: model_train={len(model_train)} "
            f"calibration={len(calibration)} test={len(test)} "
            f"calibration_target={calibration['target'].mean():.3f}"
        )
        print(f"  Selected config: {tuning.config}")
        print(f"  Inner PR-AUC: {tuning.score:.6f}")

        for method in ("raw", "sigmoid", "isotonic"):
            metrics = evaluate_probability_calibration(
                method,
                calibrated[method],
                y_test,
            )
            fold_metrics.append(
                {
                    "fold": fold_number,
                    "method": method,
                    "brier": metrics.brier,
                    "log_loss": metrics.log_loss,
                    "pr_auc": metrics.pr_auc,
                    "ece": metrics.ece,
                }
            )
            print(
                f"  {method:8s}: "
                f"Brier={metrics.brier:.6f} "
                f"LogLoss={metrics.log_loss:.6f} "
                f"PR-AUC={metrics.pr_auc if metrics.pr_auc is not None else float('nan'):.6f} "
                f"ECE={metrics.ece:.6f}"
            )

    results = pd.DataFrame(fold_metrics)
    print("Aggregate mean by method:")
    for method, group in results.groupby("method", sort=False):
        valid_pr = group["pr_auc"].dropna()
        print(
            f"  {method:8s}: "
            f"Brier={group['brier'].mean():.6f} "
            f"LogLoss={group['log_loss'].mean():.6f} "
            f"PR-AUC={valid_pr.mean() if not valid_pr.empty else float('nan'):.6f} "
            f"ECE={group['ece'].mean():.6f}"
        )

    print("REAL OOS PROBABILITY CALIBRATION SMOKE TEST PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--calibration-size", type=int, default=40)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.calibration_size <= 0:
        raise SystemExit("calibration-size must be positive")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    _run(
        args.asset_type,
        args.symbol,
        args.days,
        args.gap,
        args.calibration_size,
        args.chunk_delay,
    )


if __name__ == "__main__":
    main()
