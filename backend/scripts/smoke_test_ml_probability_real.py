from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
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


def _ece(y_true: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(y_true)
    result = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (
            (probability >= left)
            & (probability < right if right < 1.0 else probability <= right)
        )
        if not mask.any():
            continue
        result += (mask.sum() / total) * abs(
            y_true[mask].mean() - probability[mask].mean()
        )
    return float(result)


def _run(asset_type: str, symbol: str, days: int, gap: int, chunk_delay: float) -> None:
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
    folds = build_walk_forward_splits(len(dataset), n_splits=3, test_size=40, gap=gap)
    feature_list = list(feature_columns(asset_type))
    scored_lookup = scored.set_index(date_column)

    parts: list[pd.DataFrame] = []
    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start:fold.train_end].copy()
        test = dataset.iloc[fold.test_start:fold.test_end].copy()

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=TuningConfig(
                n_inner_splits=2,
                inner_test_size=20,
                gap=gap,
            ),
        )
        model = fit_baseline_model(train, asset_type=asset_type, config=tuning.config)
        probability = model.predict_proba(test[feature_list])[:, 1]

        for index, (_, test_row) in enumerate(test.iterrows()):
            latest = scored_lookup.loc[test_row[date_column]]
            risk = risk_fn(latest)
            signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                risk.adjustment,
            )
            parts.append(
                {
                    "fold": fold_number,
                    "probability": signal.ml_probability,
                    "target": int(test_row["target"]),
                    "signal_score": signal.signal_score,
                    "technical_score": signal.technical_score,
                    "risk_adjustment": signal.risk_adjustment,
                }
            )

    oos = pd.DataFrame(parts)
    y = oos["target"].to_numpy(dtype=int)
    p = oos["probability"].to_numpy(dtype=float)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"OOS rows: {len(oos)}")
    print(f"Observed target rate: {y.mean():.6f}")
    print(f"Mean predicted probability: {p.mean():.6f}")
    print(f"Probability bias (mean_p - target_rate): {p.mean() - y.mean():.6f}")
    print(f"Brier: {brier_score_loss(y, p):.6f}")
    print(f"LogLoss: {log_loss(y, p, labels=[0, 1]):.6f}")
    print(f"PR-AUC: {average_precision_score(y, p):.6f}")
    print(f"ECE: {_ece(y, p):.6f}")
    print("Probability bins:")
    edges = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 1.01]
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (p >= left) & (p < right)
        if not mask.any():
            continue
        print(
            f"  [{left:.2f}, {right if right <= 1 else 1.00:.2f}) "
            f"n={mask.sum():3d} mean_p={p[mask].mean():.4f} "
            f"target_rate={y[mask].mean():.4f}"
        )
    print("By fold:")
    for fold, group in oos.groupby("fold", sort=True):
        fy = group["target"].to_numpy(dtype=int)
        fp = group["probability"].to_numpy(dtype=float)
        print(
            f"  Fold {fold}: target={fy.mean():.4f} mean_p={fp.mean():.4f} "
            f"bias={fp.mean()-fy.mean():+.4f} PR-AUC={average_precision_score(fy, fp):.4f}"
            if len(np.unique(fy)) > 1
            else
            f"  Fold {fold}: target={fy.mean():.4f} mean_p={fp.mean():.4f} "
            f"bias={fp.mean()-fy.mean():+.4f} PR-AUC=None"
        )
    print("REAL ML PROBABILITY DIAGNOSTIC PASSED")


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
