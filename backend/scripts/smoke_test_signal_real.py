from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import pandas as pd

from app.analysis.features import build_inference_features, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
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
            "volume": [float(r.volume) if r.volume is not None else float("nan") for r in records],
        }
    )


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records: list = []
    chunks = tuple(provider._chunks(start_date, end_date, provider._settings.max_days_per_request))
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


def _run(asset_type: str, symbol: str, days: int, gap: int, chunk_delay: float) -> None:
    if asset_type == "stock":
        raw = _stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
        scored = calculate_stock_technical_score(indicators)
    else:
        raw = _fund_frame(symbol, days, chunk_delay)
        indicators = calculate_fund_indicators(raw)
        scored = calculate_fund_technical_score(indicators)

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    inference = build_inference_features(indicators, asset_type=asset_type)
    if dataset.empty or inference.empty:
        raise SystemExit("insufficient data for signal smoke test")

    tuning = select_best_candidate(
        dataset,
        asset_type=asset_type,
        tuning_config=TuningConfig(n_inner_splits=2, inner_test_size=20, gap=gap),
    )
    model = fit_baseline_model(dataset, asset_type=asset_type, config=tuning.config)
    latest_features = inference.iloc[[-1]][list(feature_columns(asset_type))]
    ml_probability = float(model.predict_proba(latest_features)[:, 1][0])

    latest_row = scored.iloc[-1]
    if asset_type == "stock":
        risk = calculate_stock_risk_adjustment(latest_row)
        latest_date = latest_row["trading_date"]
    else:
        risk = calculate_fund_risk_adjustment(latest_row)
        latest_date = latest_row["pricing_date"]

    signal = calculate_signal_score(
        ml_probability,
        float(latest_row["technical_score"]),
        risk.adjustment,
    )

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Raw rows: {len(raw)}")
    print(f"Training rows: {len(dataset)}")
    print(f"Inference date: {latest_date}")
    print(f"Selected config: {tuning.config}")
    print(f"Inner PR-AUC: {tuning.score:.6f}")
    print(f"ML probability: {signal.ml_probability:.6f}")
    print(f"Technical score: {signal.technical_score:.6f}")
    print(f"Risk score: {risk.risk_score:.6f}")
    print(f"Risk adjustment: {signal.risk_adjustment:.6f}")
    print(f"Signal score: {signal.signal_score:.6f}")
    print("Reasons:")
    for reason in (*risk.reasons, *signal.reasons):
        print(f"  - {reason}")
    assert 0.0 <= signal.ml_probability <= 1.0
    assert 0.0 <= signal.technical_score <= 100.0
    assert 0.0 <= risk.risk_score <= 100.0
    assert -20.0 <= signal.risk_adjustment <= 0.0
    assert 0.0 <= signal.signal_score <= 100.0
    print("REAL SIGNAL SMOKE TEST PASSED")


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
